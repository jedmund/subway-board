# config.py
import os

# Network settings
MTA_L_FEED_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l"
STOP_ID_NORTHBOUND = "L16N"
STOP_ID_SOUTHBOUND = "L16S"

# Error handling and retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5
WATCHDOG_TIMEOUT = 300  # 5 minutes
MEMORY_THRESHOLD = 50000  # Minimum free memory in bytes before GC

# Colors (in RGB565 format)
COLOR_BLUE = 0x00FF66
COLOR_RED = 0xFF0000
COLOR_YELLOW = 0xFF00FF
COLOR_WHITE = 0xFFFFFF

# Display settings
SCROLLING_ENABLED = False
SCROLL_SPEED = 0.02
SCROLL_TIMES = 5

# Data refresh settings (seconds)
DATA_REFRESH_INTERVAL = 30

# Quiet hours settings
QUIET_START_HOUR = 20    # 8 PM
QUIET_START_MIN = 0
QUIET_END_HOUR = 3       # 3 AM
QUIET_END_MIN = 30       # 30 minutes

# System settings
DEBUG_MODE = False  # Enable/disable debug logging


def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)


def get_wifi_credentials():
    """Safely retrieve WiFi credentials with fallback options."""
    ssid = os.getenv("CIRCUITPY_WIFI_SSID")
    password = os.getenv("CIRCUITPY_WIFI_PASSWORD")

    if not ssid or not password:
        # Fallback to config.toml or settings.toml if environment variables aren't set
        try:
            import toml

            with open("/config.toml", "r") as f:
                config = toml.load(f)
                ssid = config.get("wifi", {}).get("ssid")
                password = config.get("wifi", {}).get("password")
        except:
            pass

    if not ssid or not password:
        raise ValueError("Wi-Fi credentials not found in env vars or config files")

    return ssid, password
