import time
from config import (
    debug_print,
    COLOR_WHITE,
    COLOR_RED,
    COLOR_YELLOW,
    COLOR_BLUE,
    DEBUG_MODE,
)
from partial_protobuf_feed import parse_feed_message


def get_feed_data(connection_manager, feed_url):
    """Fetch and parse the MTA feed data."""
    feed_data = connection_manager.fetch_with_retry(feed_url)
    if not feed_data:
        raise Exception("Failed to fetch feed")

    debug_print("\nParsing feed data...")
    feed_dict = parse_feed_message(feed_data)

    debug_print(f"Keys in feed_dict: {feed_dict.keys()}")
    if "entity" in feed_dict:
        debug_print(f"Number of entities: {len(feed_dict['entity'])}")
        if feed_dict["entity"]:
            debug_print("First entity structure:", feed_dict["entity"][0].keys())

    return feed_dict


def get_train_times(feed_dict, stop_id):
    now = time.time()
    arrivals = []

    debug_print(f"\nProcessing stop_id: {stop_id}")
    debug_print(f"Current time: {now}")
    debug_print(f"Number of entities: {len(feed_dict.get('entity', []))}")

    for entity in feed_dict.get("entity", []):
        trip_update = entity.get("trip_update")
        if not trip_update:
            debug_print("No trip_update in entity")
            continue

        trip_id = trip_update.get("trip", {}).get("trip_id", "Unknown")
        debug_print(f"\nAnalyzing trip_update: {trip_id}")

        stop_time_updates = trip_update.get("stop_time_update", [])
        debug_print(f"Number of stop_time_updates: {len(stop_time_updates)}")

        for stu in stop_time_updates:
            current_stop = stu.get("stop_id")
            debug_print(f"  Stop: {current_stop} (looking for {stop_id})")

            if current_stop == stop_id:
                arr_time = stu.get("arrival_time")
                dep_time = stu.get("departure_time")

                debug_print(f"  Found matching stop!")
                debug_print(f"  Arrival time: {arr_time}")
                debug_print(f"  Departure time: {dep_time}")

                best_t = dep_time if dep_time else arr_time

                if best_t and best_t >= now:
                    mins = int((best_t - now) // 60)
                    debug_print(f"  Valid future time: {mins} minutes from now")
                    arrivals.append((trip_id, mins))
                else:
                    if not best_t:
                        debug_print("  No valid time found")
                    else:
                        debug_print(
                            f"  Time in past: {(best_t - now) / 60:.1f} minutes ago"
                        )
            else:
                debug_print(f"  Stop ID mismatch")

    result = sorted(arrivals, key=lambda x: x[1])[:3]
    debug_print(f"\nFinal arrivals for {stop_id}: {result}")

    return result


def format_train_display(arrivals, direction):
    """
    Build a text string + matching colors so each character is assigned
    the correct color. This ensures the digit(s) get the intended color,
    not the 'm' or space.
    """
    if not arrivals:
        # If no arrivals, just say: "Bkln No trains" (for example).
        text = f"{direction} No trains"
        # Colors: direction in BLUE, "No trains" in WHITE
        colors = [COLOR_BLUE] * len(direction) + [COLOR_WHITE] * len(" No trains")
        return text, colors

    # 1) Start with your direction label (e.g. "Bkln")
    text = direction
    # All those characters in direction => BLUE
    colors = [COLOR_BLUE] * len(direction)

    for i, (_, mins) in enumerate(arrivals):
        # 2) Build the next arrival snippet, e.g. " 9m" or " 12m"
        #    starting with a leading space
        time_text = f" {mins}m"

        # Decide color for the numeric portion
        if mins < 2:
            mins_color = COLOR_RED
        elif mins < 5:
            mins_color = COLOR_YELLOW
        else:
            mins_color = COLOR_WHITE

        # 3) Append the snippet to the text
        text += time_text

        # 4) Build a color list that matches every character in time_text
        #    " 9m" => [space, digit(s), 'm']
        sub_colors = []

        # The first character is space => use WHITE (or your preference)
        sub_colors.append(COLOR_WHITE)

        # For each digit in str(mins), use mins_color
        for digit in str(mins):
            sub_colors.append(mins_color)

        # The last char is 'm' => use mins_color
        sub_colors.append(mins_color)

        # 5) Extend your main colors array
        colors.extend(sub_colors)

        # 6) If there are more arrivals to come, add a comma
        if i < len(arrivals) - 1:
            text += ","
            # Add color for the comma => typically WHITE
            colors.append(COLOR_WHITE)

    return text, colors
