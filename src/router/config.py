"""Global configuration constants and shared state for the MQTT router."""

import os
import random
import threading
import time

BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
BROKER_WS_PORT = int(os.getenv("MQTT_WS_PORT", 9001))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Override this with env var IFRAMIX_BASE_PATH to relocate runtime data.
BASE_PATH = os.path.abspath(os.getenv("IFRAMIX_BASE_PATH", SCRIPT_DIR))
DB_FILE = os.path.join(BASE_PATH, "icharguard.db")

# Device registry — maps device UUID -> latest known info (in-memory cache)
devices = {}
devices_lock = threading.Lock()


def generate_msg_id():
    """Generate a snowflake-style message ID (timestamp_ms << 22 | random)."""
    return (int(time.time() * 1000) << 22) | random.randint(0, (1 << 22) - 1)
