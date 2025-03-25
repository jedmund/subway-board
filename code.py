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
        connection_manager.sync_time(tz_offset=0)  # Eastern Time

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


def main():
    """Main program loop for MTA train display."""
    try:
        connection_manager, display = initialize_system()
    except Exception as e:
        # If initialization fails, we can't continue
        print(f"Fatal error during initialization: {e}")
        return

    while True:
        try:
            # Get and parse feed data
            feed_dict = get_feed_data(connection_manager, MTA_L_FEED_URL)

            # Get train times
            north_arrivals = get_train_times(feed_dict, STOP_ID_NORTHBOUND)
            south_arrivals = get_train_times(feed_dict, STOP_ID_SOUTHBOUND)

            # Format and display train times
            north_text, north_colors = format_train_display(north_arrivals, "City")
            south_text, south_colors = format_train_display(south_arrivals, "Bkln")

            # Update display
            display.update_display(
                north_text,
                north_colors,
                south_text,
                south_colors,
                scroll_times=SCROLL_TIMES,
            )

            # Wait before next refresh
            time.sleep(DATA_REFRESH_INTERVAL)

        except Exception as e:
            display_error(display, e)
            # Attempt to reinitialize system components
            try:
                connection_manager, display = initialize_system()
            except Exception as reinit_error:
                print(f"Failed to reinitialize: {reinit_error}")
                time.sleep(30)  # Wait before retrying


if __name__ == "__main__":
    main()
