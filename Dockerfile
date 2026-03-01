FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Python and minimal system dependencies
RUN apt-get update && \
    apt-get install -y python3.10 python3.10-venv python3-pip libssl-dev ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first, then install dependencies
COPY app/requirements.txt /app/requirements.txt
RUN python3.10 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Apply verifier.py patch inside the venv so the container runtime has the fix
RUN /app/venv/bin/python - <<'PY'
import sysconfig, os, sys
try:
        site = sysconfig.get_paths()['purelib']
except Exception:
        print('Could not determine site-packages path; skipping verifier patch')
        sys.exit(0)

verifier_path = os.path.join(site, 'ask_sdk_webservice_support', 'verifier.py')
if not os.path.exists(verifier_path):
        print('verifier.py not found at', verifier_path, '; skipping patch')
        sys.exit(0)

with open(verifier_path, 'r', encoding='utf-8') as f:
        src = f.read()

needle = (
    '        now = datetime.utcnow()\n'
    '        if not (x509_cert.not_valid_before <= now <=\n'
    '                x509_cert.not_valid_after):\n'
    '            raise VerificationException("Signing Certificate expired")'
)
patch = (
    '        from datetime import timezone\n'
    '        now = datetime.now(timezone.utc)\n'
    '        # Use timezone-aware UTC datetimes and updated cryptography properties\n'
    "        not_valid_before = getattr(x509_cert, 'not_valid_before_utc', None) or x509_cert.not_valid_before.replace(tzinfo=timezone.utc)\n"
    "        not_valid_after = getattr(x509_cert, 'not_valid_after_utc', None) or x509_cert.not_valid_after.replace(tzinfo=timezone.utc)\n"
    '        if not (not_valid_before <= now <= not_valid_after):\n'
    '            raise VerificationException("Signing Certificate expired")'
)

if needle in src:
    new_src = src.replace(needle, patch)
    backup = verifier_path + '.orig'
    try:
        if not os.path.exists(backup):
            with open(backup, 'w', encoding='utf-8') as b:
                b.write(src)
        with open(verifier_path, 'w', encoding='utf-8') as f:
            f.write(new_src)
        print('Patched', verifier_path, '(backup at', backup + ')')
    except Exception as e:
        print('Failed to write patch:', e)
else:
    print('No patch needed for verifier.py')
PY

# Copy application source code
COPY app /app/src
# Copy repository-level assets (icons, images)
COPY assets /app/assets

# Amazon Skill & Host Configuration
ENV AWS_DEFAULT_REGION=us-east-1

# Timezone (defaults to UTC) — can be overridden at runtime via TZ env
ENV TZ=UTC

# Host configuration
ENV STREAM_HOSTNAME=""
ENV SKILL_HOSTNAME=""
ENV PORT=5150
ENV ADMIN_PORT=5151
ENV LOCALE=en-US
# Reduce HTTP request log noise (werkzeug/urllib3)
ENV QUIET_HTTP=1

# Create non-root user
RUN useradd -m -s /bin/bash appuser && chown -R appuser:appuser /app

USER appuser

# Expose ports
EXPOSE ${PORT}
EXPOSE ${ADMIN_PORT}

CMD ["venv/bin/python", "src/entrypoint.py"]