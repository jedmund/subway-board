# config.py
import os

# Network settings

# The feed URL for the MTA line you wish to display
# Example: https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l
MTA_FEED_URL = ""

# The stop ID for the northbound train
# Example: "L16N"
STOP_ID_NORTHBOUND = ""

# The stop ID for the southbound train
# Example: "L16S"
STOP_ID_SOUTHBOUND = ""

# Data refresh settings (seconds)
DATA_REFRESH_INTERVAL = 30

# Quiet hours settings

# Quiet hours start time
# Example: 20 (8 PM)
QUIET_START_HOUR = 20

# Quiet hours start minute
# Example: 0
QUIET_START_MIN = 0

# Quiet hours end hour
# Example: 3 (3 AM)
QUIET_END_HOUR = 3

# Quiet hours end minute
# Example: 30 (30 minutes)
QUIET_END_MIN = 30

# Colors (in RGB565 format)

# Label color
COLOR_BLUE = 0x00FF66

# Arriving in less than 2 minutes
COLOR_RED = 0xFF0000

# Arriving in less than 5 minutes
COLOR_YELLOW = 0xFF00FF

# Default arrivalcolor
COLOR_WHITE = 0xFFFFFF

# Other settings

# Display settings
SCROLLING_ENABLED = False
SCROLL_SPEED = 0.02
SCROLL_TIMES = 5

# Error handling and retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5
WATCHDOG_TIMEOUT = 300  # 5 minutes
MEMORY_THRESHOLD = 50000  # Minimum free memory in bytes before GC

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
