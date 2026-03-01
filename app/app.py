import os
import sys
import json
import time
import base64
import secrets
import string
import logging
import threading
from pathlib import Path
from pathlib import Path

from flask import Flask, request, jsonify, Response, g
from flask_ask_sdk.skill_adapter import SkillAdapter
from skill.lambda_function import sb
import music_assistant_api as ma_api
import alexa_api as alexa_api
from persistent_store import store
from werkzeug.middleware.proxy_fix import ProxyFix
from env_secrets import get_env_secret


# ---------------------------------------------------------------------------
# Auto-generate credentials if secrets files don't exist
# ---------------------------------------------------------------------------
def _ensure_secrets():
    """Create secrets/ directory and credential files if they don't exist."""
    secrets_dir = Path(__file__).parent.parent / 'secrets'
    user_file = secrets_dir / 'app_username.txt'
    pass_file = secrets_dir / 'app_password.txt'

    if user_file.exists() and pass_file.exists():
        return

    secrets_dir.mkdir(parents=True, exist_ok=True)

    if not user_file.exists():
        username = 'user_' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
        user_file.write_text(username + '\n')
        print(f'[SETUP] Generated username: {username}')

    if not pass_file.exists():
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        pass_file.write_text(password + '\n')
        print(f'[SETUP] Generated password: {password}')

    print(f'[SETUP] Credentials saved in {secrets_dir}/')

# Point env vars to the secrets files so get_env_secret() can read them
def _configure_secret_env():
    """Set APP_USERNAME and APP_PASSWORD env vars to point at the secret files."""
    secrets_dir = Path(__file__).parent.parent / 'secrets'
    user_file = secrets_dir / 'app_username.txt'
    pass_file = secrets_dir / 'app_password.txt'
    if user_file.exists():
        os.environ.setdefault('APP_USERNAME', str(user_file))
    if pass_file.exists():
        os.environ.setdefault('APP_PASSWORD', str(pass_file))

_ensure_secrets()
_configure_secret_env()

# Ensure boto3 has a default region
os.environ.setdefault('AWS_REGION', os.environ.get('AWS_REGION', 'us-east-1'))
os.environ.setdefault('AWS_DEFAULT_REGION', os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))


# ---------------------------------------------------------------------------
# Public App — only the Alexa skill endpoint (exposed via tunnel)
# ---------------------------------------------------------------------------
app = Flask(__name__)

# Optionally silence HTTP request logs
try:
    quiet_http = os.environ.get('QUIET_HTTP', '1').lower()
    if quiet_http in ('1', 'true', 'yes', 'on'):
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('flask.app').setLevel(logging.WARNING)
except Exception:
    pass

skill_adapter = SkillAdapter(
    skill=sb.create(),
    skill_id="",  # pyright: ignore[reportArgumentType]
    app=app)

# Respect X-Forwarded-* headers when running behind a reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


# Capture incoming Alexa POST payloads for the invocations log
@app.before_request
def _capture_incoming_intent():
    if request.path == '/' and request.method == 'POST':
        payload = None
        try:
            payload = request.get_json(silent=True)
        except Exception:
            payload = None
        if not payload:
            try:
                raw = request.get_data(as_text=True)
                if raw:
                    try:
                        payload = json.loads(raw)
                    except Exception:
                        payload = None
            except Exception:
                payload = None

        g._incoming_alexa_payload = payload or {}
        g._incoming_alexa_ts = time.time()


@app.after_request
def _record_incoming_intent(response):
    if getattr(g, '_incoming_alexa_payload', None) is not None:
        try:
            entry = {
                'incoming': g._incoming_alexa_payload,
                'response_status': response.status_code,
                'response_body': response.get_data(as_text=True),
                'ts': getattr(g, '_incoming_alexa_ts', None)
            }
            store.add_intent_log(entry)
        except Exception:
            pass
    return response


# Centralized intent logs (Legacy configuration removed in favor of persistent_store)


@app.route("/", methods=["POST"])
def invoke_skill():
    """Alexa skill endpoint — full signature verification required."""
    return skill_adapter.dispatch_request()


# ---------------------------------------------------------------------------
# Admin App — status, invocations, MA API, Alexa API (local only)
# ---------------------------------------------------------------------------
admin_app = Flask('admin')
admin_app.wsgi_app = ProxyFix(admin_app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Intent logs are now managed by persistent_store.py


class BasicAuthMiddleware:
    """WSGI middleware that enforces HTTP Basic auth using APP_USERNAME/APP_PASSWORD."""
    def __init__(self, wsgi_app):
        self.app = wsgi_app

    def __call__(self, environ, start_response):
        user = get_env_secret('APP_USERNAME')
        pwd = get_env_secret('APP_PASSWORD')
        if not user and not pwd:
            return self.app(environ, start_response)

        auth = environ.get('HTTP_AUTHORIZATION')
        if auth and auth.startswith('Basic '):
            try:
                token = auth.split(' ', 1)[1].strip()
                decoded = base64.b64decode(token).decode('utf-8')
                u, sep, p = decoded.partition(':')
                if sep and u == user and p == pwd:
                    return self.app(environ, start_response)
            except Exception:
                pass

        start_response('401 Unauthorized', [
            ('Content-Type', 'text/plain'),
            ('WWW-Authenticate', 'Basic realm="music-assistant-skill"')
        ])
        return [b'Access denied']


# Mount MA and Alexa sub-apps on the admin app
ma_flask_app = ma_api.create_ma_app()
alexa_flask_app = alexa_api.create_alexa_app()

# Register status and invocations blueprints on the admin app
try:
    from endpoints import status_bp, invocations_bp
    admin_app.register_blueprint(status_bp)
    admin_app.register_blueprint(invocations_bp)
except Exception:
    print('[WARN] Could not register endpoints blueprints')

# Mount sub-apps on admin using DispatcherMiddleware
from werkzeug.middleware.dispatcher import DispatcherMiddleware
admin_app.wsgi_app = DispatcherMiddleware(admin_app.wsgi_app, {
    '/ma': ma_flask_app.wsgi_app,
    '/alexa': alexa_flask_app.wsgi_app,
})

# Protect the entire admin app with Basic Auth
admin_app.wsgi_app = BasicAuthMiddleware(admin_app.wsgi_app)


def _run_admin_server():
    """Start the admin server on ADMIN_PORT (local-only)."""
    admin_port = int(os.environ.get('ADMIN_PORT', '5151'))
    print(f'[ADMIN] Starting admin server on port {admin_port} (local only)')
    admin_app.run(host='0.0.0.0', port=admin_port, debug=False, use_reloader=False)


if __name__ == "__main__":
    # Standalone mode (without gunicorn) — starts both servers
    admin_thread = threading.Thread(target=_run_admin_server, daemon=True)
    admin_thread.start()
    port = int(os.environ.get('PORT', '5150'))
    print(f'[PUBLIC] Starting Alexa skill server on port {port}')
    app.run(debug=False, host="0.0.0.0", port=port)
