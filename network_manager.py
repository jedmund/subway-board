import time
import ssl
import wifi
import socketpool
import adafruit_requests
import rtc
import adafruit_ntp
import os
from config import MAX_RETRIES, RETRY_DELAY

class ConnectionManager:
    """Manages network connections with retry logic."""

    MAX_RETRIES = 3
    RETRY_DELAY = 5

    def __init__(self):
        # Connect to WiFi first
        self._connect_wifi()
        
        # Setup network resources
        self.pool = socketpool.SocketPool(wifi.radio)
        self.ssl_context = ssl.create_default_context()
        self.session = adafruit_requests.Session(self.pool, self.ssl_context)
        self._ntp = None

    def fetch_with_retry(self, url):
        """Fetch data from URL with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url)
                if response.status_code == 200:
                    data = response.content
                    response.close()
                    return data
                    
                response.close()
                
                # Retry on server errors
                if response.status_code in [500, 502, 503, 504]:
                    print(f"Server error {response.status_code}, retrying...")
                    time.sleep(RETRY_DELAY)
                    continue
                    
                print(f"HTTP error: {response.status_code}")
                return None
                
            except (OSError, RuntimeError) as e:
                print(f"Network error on attempt {attempt + 1}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    # Create fresh session on retry
                    self.session = adafruit_requests.Session(self.pool, self.ssl_context)
                else:
                    print("Max retries reached")
                    raise
                    
        return None

    def sync_time(self, tz_offset=0):
        """Synchronize system time using NTP."""
        # Check WiFi connection
        if not wifi.radio.connected:
            print("WiFi not connected, attempting to reconnect...")
            if not self._connect_wifi():
                return False

        for attempt in range(MAX_RETRIES):
            try:
                if self._ntp is None:
                    self._ntp = adafruit_ntp.NTP(self.pool, tz_offset=tz_offset)
                    
                rtc.RTC().datetime = self._ntp.datetime
                current_time = time.localtime()
                print(f"Time synchronized: {current_time.tm_hour:02d}:{current_time.tm_min:02d}:{current_time.tm_sec:02d}")
                return True
                
            except Exception as e:
                print(f"Time sync attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    print(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                    # Reset NTP client on retry
                    self._ntp = None
        
        print("Failed to sync time after all retries")
        return False
    
    def _connect_wifi(self):
        """Connect to WiFi using credentials from environment or settings."""
        from config import get_wifi_credentials
    
        try:
            ssid, password = get_wifi_credentials()
            print(f"Connecting to {ssid}...")

            wifi.radio.connect(ssid, password)
            print("Connected! IP:", wifi.radio.ipv4_address)
            
            return True
        except Exception as e:
            print(f"WiFi connection failed: {e}")
            return False
        
    def _get_wifi_credentials(self):
        """Get WiFi credentials from environment variables."""
        ssid = os.getenv("CIRCUITPY_WIFI_SSID")
        password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
        
        if not ssid or not password:
            raise ValueError("Wi-Fi credentials not set in environment variables")
            
        return ssid, password


def get_connection_manager():
    """Factory function to create and initialize a ConnectionManager instance."""
    try:
        return ConnectionManager()
    except Exception as e:
        print(f"Failed to initialize connection manager: {e}")
        raise
