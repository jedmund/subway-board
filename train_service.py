import time
from config import (
    debug_print,
    COLOR_WHITE,
    COLOR_RED,
    COLOR_YELLOW,
    COLOR_BLUE,
    DEBUG_MODE,
)

EST_OFFSET = -5 * 3600  # 5 hours in seconds (UTC to EST)

def get_feed_data(connection_manager, feed_url):
    """Fetch and parse the MTA feed data."""
    feed_data = connection_manager.fetch_with_retry(feed_url)
    if not feed_data:
        raise Exception("Failed to fetch feed")

    debug_print("\nParsing feed data...")
    from partial_protobuf_feed import parse_feed_message
    return parse_feed_message(feed_data)

def get_train_times(feed_dict, stop_id):
    """Get upcoming train arrivals for a specific stop."""
    now = time.time()
    arrivals = []
    
    debug_print(f"\nProcessing stop_id: {stop_id}")
    
    for entity in feed_dict.get("entity", []):
        trip_update = entity.get("trip_update")
        if not trip_update:
            continue

        trip_id = trip_update.get("trip", {}).get("trip_id", "Unknown")
        process_stop_updates(trip_update, stop_id, trip_id, now, arrivals)
    
    # Return only the next 3 arrivals, sorted by time
    return sorted(arrivals, key=lambda x: x[1])[:3]

def process_stop_updates(trip_update, stop_id, trip_id, now, arrivals):
    """Process stop time updates for a trip."""
    for stu in trip_update.get("stop_time_update", []):
        if stu.get("stop_id") != stop_id:
            continue
            
        # Use departure time if available, otherwise use arrival time
        arr_time = stu.get("arrival_time")
        dep_time = stu.get("departure_time")
        best_time = dep_time if dep_time else arr_time
        
        if not best_time or best_time < now:
            continue
            
        # Convert UTC to EST
        local_time = best_time + EST_OFFSET
        mins = int((local_time - now) // 60)
        
        arrivals.append((trip_id, mins))

def get_time_color(mins):
    """Return the appropriate color based on arrival time."""
    if mins < 2:
        return COLOR_RED
    elif mins < 5:
        return COLOR_YELLOW
    else:
        return COLOR_WHITE
    
def format_train_display(arrivals, direction):
    """Format train arrivals for display with appropriate colors."""
    if not arrivals:
        text = f"{direction} No trains"
        colors = [COLOR_BLUE] * len(direction) + [COLOR_WHITE] * len(" No trains")
        return text, colors

    # Start with the direction
    text = direction
    colors = [COLOR_BLUE] * len(direction)

    # Add each arrival time
    for i, (_, mins) in enumerate(arrivals):
        time_text = f" {mins}m"
        text += time_text
        
        # Determine color for this arrival
        mins_color = get_time_color(mins)
        
        # Add colors for each character
        colors.append(COLOR_WHITE)  # space
        for _ in str(mins):
            colors.append(mins_color)  # digits
        colors.append(mins_color)  # 'm'
        
        # Add comma if not the last arrival
        if i < len(arrivals) - 1:
            text += ","
            colors.append(COLOR_WHITE)

    return text, colors
