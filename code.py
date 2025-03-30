from config import (
    MTA_L_FEED_URL,
    STOP_ID_NORTHBOUND,
    STOP_ID_SOUTHBOUND,
    COLOR_RED,
    SCROLL_SPEED,
    DATA_REFRESH_INTERVAL,
    SCROLL_TIMES,
)
from display_manager import Display
from network_manager import get_connection_manager
import time
from train_service import get_feed_data, get_train_times, format_train_display


def initialize_system():
    """Initialize system components and establish network connection."""
    try:
        # Initialize network and time
        connection_manager = get_connection_manager()
        connection_manager.sync_time(tz_offset=-5)  # Eastern Standard Time

        # Initialize display
        display = Display(scroll_speed=SCROLL_SPEED)

        return connection_manager, display
    except Exception as e:
        print(f"Initialization error: {e}")
        raise


def display_error(display, error_msg):
    """Display error message on both lines of the display."""
    print("Error:", error_msg)
    display.set_text_with_colors("Error", [COLOR_RED], 0)
    display.set_text_with_colors(str(error_msg), [COLOR_RED], 1)
    time.sleep(5)

def fetch_train_data(connection_manager):
    """Fetch and process train data."""
    try:
        # Get and parse feed data
        feed_dict = get_feed_data(connection_manager, MTA_L_FEED_URL)
        
        # Get train times
        north_arrivals = get_train_times(feed_dict, STOP_ID_NORTHBOUND)
        south_arrivals = get_train_times(feed_dict, STOP_ID_SOUTHBOUND)
        
        # Format train display
        north_text, north_colors = format_train_display(north_arrivals, "City")
        south_text, south_colors = format_train_display(south_arrivals, "Bkln")
        
        return north_text, north_colors, south_text, south_colors
    except Exception as e:
        print(f"Error fetching train data: {e}")
        return None, None, None, None


def main():
    """Main program loop for MTA train display."""
    try:
        connection_manager, display = initialize_system()

        # Ignore any false button presses at boot
        display.last_button_state = not display.button_up.value
        print(f"Initial button state: {display.last_button_state}")

        # Check appropriate mode based on time when first starting
        if display.is_quiet_hours():
            display.show_night_mode()
        else:
            display.show_normal_mode()
    except Exception as e:
        print(f"Fatal error during initialization: {e}")
        return

    # Initial data fetch
    north_text, north_colors, south_text, south_colors = fetch_train_data(connection_manager)
    
    # Check appropriate mode based on time when first starting
    if display.is_quiet_hours():
        display.show_night_mode()
    else:
        display.show_normal_mode()
        # Show initial data if in normal mode and data available
        if north_text and south_text:
            display._static_display(north_text, north_colors, south_text, south_colors)

    last_refresh_time = time.monotonic()

    while True:
        try:
            # Check button continuously
            button_result = display.check_button()
            
            current_time = time.monotonic()
            need_refresh = False
            
            # If night mode was turned OFF, need fresh data
            if button_result == 2:
                need_refresh = True
            
            # Or if it's time for regular refresh
            if current_time - last_refresh_time >= DATA_REFRESH_INTERVAL:
                need_refresh = True
                last_refresh_time = current_time
            
            # Fetch new data if needed
            if need_refresh:
                north_text, north_colors, south_text, south_colors = fetch_train_data(connection_manager)
                
                # Skip button check if this refresh was triggered by button press
                if button_result == 2:
                    display._static_display(north_text, north_colors, south_text, south_colors)
                else:
                    display.update_display(
                        north_text,
                        north_colors,
                        south_text,
                        south_colors,
                        scroll_times=SCROLL_TIMES,
                    )
            
            # Small delay to prevent CPU hogging
            time.sleep(0.1)

        except Exception as e:
            display_error(display, e)
            try:
                connection_manager, display = initialize_system()
            except Exception as reinit_error:
                print(f"Failed to reinitialize: {reinit_error}")
                time.sleep(30)


if __name__ == "__main__":
    main()
