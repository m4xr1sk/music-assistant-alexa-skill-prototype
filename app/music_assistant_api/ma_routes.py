"""Route definitions for music_assistant_api (ma_routes).

This module registers the HTTP endpoints on a provided Flask
`Blueprint`. It stores the last pushed stream metadata in a
module-level `_store` variable.
"""

from flask import jsonify, request
import time


from persistent_store import store


def register_routes(bp):
    @bp.route('/push-url', methods=['POST'])
    def push_url():
        """Accept JSON with streamUrl and optional metadata and store it.

        Expected JSON body: { streamUrl, title, artist, album, imageUrl }
        """
        data = request.get_json(silent=True) or {}
        stream_url = data.get('streamUrl')
        
        # Get current state to increment version
        current_store = store.get_ma_store() or {}
        version = current_store.get('version', 0) + 1
        
        payload = {
            'streamUrl': stream_url,
            'title': data.get('title'),
            'artist': data.get('artist'),
            'album': data.get('album'),
            'imageUrl': data.get('imageUrl'),
            'playerId': data.get('playerId'),
            'version': version,
            'timestamp': time.time()
        }
        store.set_ma_store(payload)
        return jsonify({'status': 'ok', 'version': version})

    @bp.route('/latest-url', methods=['GET'])
    def latest_url():
        """Return the last pushed stream metadata for the Music Assistant.
        """
        ma_store = store.get_ma_store()
        if not ma_store:
            return jsonify({'error': 'No URL available, please check if Music Assistant has pushed a URL to the API'}), 404
        return jsonify(ma_store)
