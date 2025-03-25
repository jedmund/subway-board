import time
import ssl
import wifi
import socketpool
import adafruit_requests
import rtc
import adafruit_ntp
import os


class ConnectionManager:
    """Manages network connections with retry logic."""

    MAX_RETRIES = 3
    RETRY_DELAY = 5

    def __init__(self):
        self.pool = socketpool.SocketPool(wifi.radio)
        self.ssl_context = ssl.create_default_context()
        self.session = adafruit_requests.Session(self.pool, self.ssl_context)
        self._ntp = None

    def fetch_with_retry(self, url):
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(url)
                if response.status_code == 200:
                    data = response.content
                    response.close()
                    return data
                response.close()
                if response.status_code in [500, 502, 503, 504]:
                    print(f"Server error {response.status_code}, retrying...")
                    time.sleep(self.RETRY_DELAY)
                    continue
                print(f"HTTP error: {response.status_code}")
                return None
            except (OSError, RuntimeError) as e:
                print(f"Network error on attempt {attempt + 1}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                    self.session = adafruit_requests.Session(
                        self.pool, self.ssl_context
                    )
                else:
                    print("Max retries reached")
                    raise
        return None

    def sync_time(self, tz_offset=0):
        """Synchronizes the system time using NTP.

        Args:
            tz_offset (int): Timezone offset from UTC in hours
        """
        try:
            if self._ntp is None:
                self._ntp = adafruit_ntp.NTP(self.pool, tz_offset=tz_offset)
            rtc.RTC().datetime = self._ntp.datetime
            current_time = time.localtime()
            print(
                f"Time synchronized: {current_time.tm_hour:02d}:{current_time.tm_min:02d}:{current_time.tm_sec:02d}"
            )
            return True
        except Exception as e:
            print(f"Failed to sync time: {e}")
            return False


def connect_wifi():
    """Establishes Wi-Fi connection using credentials from environment variables."""
    ssid = os.getenv("CIRCUITPY_WIFI_SSID")
    password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
    if not ssid or not password:
        raise ValueError("Wi-Fi credentials not set in environment variables.")
    print(f"Connecting to {ssid}...")
    wifi.radio.connect(ssid, password)
    print("Connected! IP:", wifi.radio.ipv4_address)


def get_connection_manager():
    """Factory function to create and initialize a ConnectionManager instance."""
    try:
        connect_wifi()
        return ConnectionManager()
    except Exception as e:
        print(f"Failed to initialize connection manager: {e}")
        raise
