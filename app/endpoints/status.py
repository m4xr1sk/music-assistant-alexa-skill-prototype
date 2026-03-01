from flask import Blueprint, request, jsonify, Response, current_app
from markupsafe import escape
import json
import os
import re
import shutil
import subprocess
import urllib.parse

import requests
from requests.exceptions import RequestException
from env_secrets import get_env_secret
from pathlib import Path
from persistent_store import store

status_bp = Blueprint('status_bp', __name__)


def _build_status_json():
    api_user = get_env_secret('APP_USERNAME')
    api_pass = get_env_secret('APP_PASSWORD')
    skill_html = '<span class="status-indicator online"></span> Skill running'

    # MA API check
    endpoint_url = request.host_url.rstrip('/') + '/ma/latest-url'
    try:
        auth = (api_user, api_pass) if api_user and api_pass else None
        resp = requests.get(endpoint_url, timeout=2, auth=auth)
        content_preview = escape(resp.text)
        try:
            parsed = resp.json()
            content_preview = escape(json.dumps(parsed, indent=2, ensure_ascii=False))
        except Exception:
            pass
            
        if resp.ok:
            ma_api_html = (
                f'<div class="status-item"><span class="status-indicator online"></span> Music Assistant API reachable ({resp.status_code})</div>'
                f"<pre class='code-block'>{content_preview}</pre>"
            )
        else:
            ma_api_html = (
                f'<div class="status-item"><span class="status-indicator offline"></span> Music Assistant API responded {resp.status_code}</div>'
                f"<pre class='code-block error'>{content_preview}</pre>"
            )
    except Exception as e:
        ma_api_html = f'<div class="status-item"><span class="status-indicator offline"></span> Error: {escape(str(e))}</div>'

    # lightweight invocations link
    intent_logs = store.get_intent_logs()
    count = len(intent_logs)
    if count:
        invocations_html = f'<a href="/invocations" class="btn-link">Invocations Log ({count})</a>'
    else:
        invocations_html = '<button class="btn-link" disabled style="opacity: 0.5; cursor: not-allowed; border: none;">Invocations Log (0)</button>'

    return {'skill_html': skill_html, 'ma_api_html': ma_api_html, 'metadata_html': metadata_html, 'invocations_html': invocations_html}


def _compute_ma_api_html(api_user=None, api_pass=None):
    api_user = api_user or get_env_secret('APP_USERNAME')
    api_pass = api_pass or get_env_secret('APP_PASSWORD')
    endpoint_url = (request.host_url.rstrip('/') if request else '') + '/ma/latest-url'
    try:
        auth = (api_user, api_pass) if api_user and api_pass else None
        resp = requests.get(endpoint_url, timeout=2, auth=auth)
        try:
            content_text = resp.content.decode('utf-8', errors='replace')
        except Exception:
            content_text = str(resp.content)
        try:
            parsed = json.loads(content_text)
            pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
            content_preview = escape(pretty)
        except Exception:
            content_preview = escape(content_text)
        if resp.ok:
            return (
                f'<div class="status-item"><span class="status-indicator online"></span> Music Assistant API reachable ({resp.status_code})</div>'
                f"<p class=\"text-muted\" style=\"margin-top:0; font-size:0.85em\">Latest data received from the Music Assistant server via webhook.</p>"
                f"<pre class='code-block'>{content_preview}</pre>"
            )
        else:
            return (
                f'<div class="status-item"><span class="status-indicator offline"></span> Music Assistant API responded {resp.status_code}</div>'
                f"<pre class='code-block error'>{content_preview}</pre>"
            )
    except RequestException as e:
        return f'<div class="status-item"><span class="status-indicator offline"></span> Error: {escape(str(e))}</div>'


@status_bp.route('/status/ma', methods=['GET'])
def status_ma():
    return jsonify({'ma_api_html': _compute_ma_api_html()})


def _compute_metadata_html():
    """Compute HTML showing the current APL metadata being sent in refreshes."""
    try:
        metadata_info = store.get_ma_store() or {}
        
        pretty_metadata = json.dumps(metadata_info, indent=2, ensure_ascii=False)
        content_preview = escape(pretty_metadata)
        
        if metadata_info.get('streamUrl') or metadata_info.get('title'):
            return (
                f'<div class="status-item"><span class="status-indicator online"></span> APL Metadata Refresh (current data)</div>'
                f"<pre class='code-block'>{content_preview}</pre>"
            )
        else:
            return (
                f'<div class="status-item"><span class="status-indicator warning"></span> APL Metadata Refresh (no data loaded yet)</div>'
                f"<pre class='code-block warning'>{content_preview}</pre>"
            )
    except Exception as e:
        return f'<div class="status-item"><span class="status-indicator offline"></span> Error loading metadata: {escape(str(e))}</div>'


@status_bp.route('/status/metadata', methods=['GET'])
def status_metadata():
    return jsonify({'metadata_html': _compute_metadata_html()})

@status_bp.route('/', methods=['GET'])
def status():
    # If client requested JSON, return the aggregated checks
    want_json = request.args.get('format') == 'json' or 'application/json' in (request.headers.get('Accept') or '')
    if want_json:
        return jsonify(_build_status_json())

    # Non-JSON: render status template
    try:
        tpl_path = Path(__file__).parent.parent / 'templates' / 'status.html'
        tpl = tpl_path.read_text(encoding='utf-8')
        tpl = tpl.replace('__SKILL_HTML__', '<span class="status-indicator online"></span> Skill running')
        tpl = tpl.replace('__MA_API_HTML__', '<span class="text-muted">Checking Music Assistant API...</span>')
        tpl = tpl.replace('__METADATA_HTML__', '<span class="text-muted">Loading APL metadata...</span>')
        
        intent_logs = store.get_intent_logs()
        count = len(intent_logs)
        if count:
            invocations_html = f'<a href="/invocations" class="btn-link">Invocations Log ({count})</a>'
        else:
            invocations_html = '<button class="btn-link" disabled style="opacity: 0.5; cursor: not-allowed; border: none;">Invocations Log (0)</button>'
        tpl = tpl.replace('__INVOCATIONS_HTML__', invocations_html)
        return Response(tpl, status=200, mimetype='text/html')
    except Exception:
        html = """<!doctype html>
            <html>
            <head><meta charset="utf-8"><title>Service Status</title></head>
            <body>
                <h1>Service Status</h1>
                <div><span class=\"led green\"></span> Skill running</div>
                <div><span class=\"muted\">Checking ASK CLI status...</span></div>
                <div><span class=\"muted\">Checking Music Assistant API...</span></div>
            </body>
            </html>"""
        return Response(html, status=200, mimetype='text/html')


@status_bp.route('/status/api', methods=['GET'])
def status_api():
    """Lightweight API used by the status UI to fetch aggregated checks."""
    return jsonify(_build_status_json())

@status_bp.route('/status/invocations', methods=['GET'])
def status_invocations():
    """Return the current invocation count and invocation HTML so the UI can refresh it live."""
    intent_logs = store.get_intent_logs()
    count = len(intent_logs)
    if count:
        invocations_html = f'<a href="/invocations" class="btn-link">Invocations Log ({count})</a>'
    else:
        invocations_html = '<button class="btn-link" disabled style="opacity: 0.5; cursor: not-allowed; border: none;">Invocations Log (0)</button>'
    return jsonify({'count': count, 'invocations_html': invocations_html})
