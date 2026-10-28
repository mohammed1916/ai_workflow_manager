from __future__ import annotations
import hashlib, os
from datetime import datetime, timezone

class RelayError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.status = code, status

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def _read_env_config(root):
    config = dict(os.environ)
    env = root / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1)
                config.setdefault(k.strip(), v.strip().strip('"\''))
    return config

def read_config(root):
    """Configuration from the environment and .env. Hosted mode never uses keys set on the server."""
    config = _read_env_config(root)
    if os.environ.get('RELAY_HOSTED') == '1':
        for field in ('NEBIUS_API_KEY', 'OLLAMA_TEST_API_KEY', 'OLLAMA_API_KEY', 'TAVILY_API_KEY'): config.pop(field, None)
    return config
