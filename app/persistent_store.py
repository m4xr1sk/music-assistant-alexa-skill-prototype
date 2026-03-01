import os
import json
import logging
import threading
import time
from pathlib import Path

class PersistentStore:
    """A simple file-based persistent store for sharing state between processes."""
    
    def __init__(self, filename="persistent_state.json"):
        # Store file in the same directory as this script, or use a provided path
        self.file_path = Path(__file__).parent / filename
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self):
        if not self.file_path.exists():
            self._write_json({"ma_store": None, "alexa_store": None, "intent_logs": []})

    def _read_json(self):
        try:
            if not self.file_path.exists():
                return {}
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            logging.error(f"Failed to read persistent store at {self.file_path}", exc_info=True)
            return {}

    def _write_json(self, data):
        try:
            # Atomic write using a temporary file
            temp_path = self.file_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self.file_path)
        except Exception:
            logging.error(f"Failed to write persistent store at {self.file_path}", exc_info=True)

    def get_ma_store(self):
        with self._lock:
            return self._read_json().get("ma_store")

    def set_ma_store(self, data):
        with self._lock:
            state = self._read_json()
            state["ma_store"] = data
            self._write_json(state)

    def get_alexa_store(self):
        with self._lock:
            return self._read_json().get("alexa_store")

    def set_alexa_store(self, data):
        with self._lock:
            state = self._read_json()
            state["alexa_store"] = data
            self._write_json(state)

    def add_intent_log(self, entry, max_len=500):
        with self._lock:
            state = self._read_json()
            logs = state.get("intent_logs", [])
            logs.append(entry)
            if len(logs) > max_len:
                logs = logs[-max_len:]
            state["intent_logs"] = logs
            self._write_json(state)

    def get_intent_logs(self):
        with self._lock:
            return self._read_json().get("intent_logs", [])

# Global singleton instance
store = PersistentStore()
