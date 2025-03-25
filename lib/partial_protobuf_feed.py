"""
Minimal Protobuf wire-format parser for the MTA L-train feed in CircuitPython.
Parses the *actual* structure seen in your "protoc --decode_raw" output:

Top-level:
  1 { ... } => header
  2 { ... } => repeated entity
  2 { ... }
  etc.

Within header (field_num=1):
  subfield #1 => "1.0" (string)
  subfield #2 => int (often 0)
  subfield #3 => feed timestamp
  subfield #1001 => NYCT extension (we skip or partially parse)

Within each entity (field_num=2 repeated):
  subfield #1 => entity ID string (e.g. "1","2", etc.)
  subfield #2 => int (often 0)
  subfield #3 => trip update data
  subfield #4 => vehicle or extension data

We parse enough to find trip updates and stop_time_updates that contain, e.g., "L16N"/"L16S."
"""

import time

# Protobuf wire-type constants
VARINT = 0
FIXED64 = 1
LENGTH_DELIMITED = 2
START_GROUP = 3  # obsolete
END_GROUP = 4  # obsolete
FIXED32 = 5


def parse_varint(data, index):
    """
    Parse a 'varint' from Protobuf wire format starting at data[index].
    Returns (value, new_index).
    """
    shift = 0
    result = 0
    while True:
        b = data[index]
        index += 1
        result |= (b & 0x7F) << shift
        shift += 7
        if not (b & 0x80):
            break
    return result, index


def parse_key(data, index):
    """
    Parse the Protobuf 'key' => (field_number << 3) | wire_type.
    Returns (field_number, wire_type, new_index).
    """
    val, index = parse_varint(data, index)
    field_num = val >> 3
    wire_type = val & 0x07
    return field_num, wire_type, index


def parse_length_delimited(data, index):
    """
    Parse a LENGTH_DELIMITED field, returning (sub_bytes, new_index).
    """
    length, index = parse_varint(data, index)
    sub_bytes = data[index : index + length]
    return sub_bytes, index + length


def skip_field(data, wire_type, index):
    """
    Skip over an unused field based on wire_type.
    Returns new_index after skipping.
    """
    if wire_type == VARINT:
        _, index = parse_varint(data, index)
    elif wire_type == FIXED64:
        index += 8
    elif wire_type == LENGTH_DELIMITED:
        length, index = parse_varint(data, index)
        index += length
    elif wire_type == FIXED32:
        index += 4
    else:
        # START_GROUP, END_GROUP are obsolete in proto2
        pass
    return index


# ------------------------------------------------------------
# PARSE HEADER (top-level field_num=1)
# ------------------------------------------------------------
def parse_mta_header(subdata):
    """
    The 'header' block from your raw decode might look like:
       1: "1.0"
       2: 0
       3: 1734835126 (feed timestamp)
       1001 { ... } (NYCT extension)
    We'll store feed_version => field #1, feed_timestamp => field #3,
    and skip everything else.
    """
    idx = 0
    end = len(subdata)
    header = {
        "gtfs_realtime_version": None,
        "timestamp": 0,
    }

    while idx < end:
        field_num, wire_type, idx = parse_key(subdata, idx)

        if field_num == 1 and wire_type == LENGTH_DELIMITED:
            # e.g. "1.0"
            raw_bytes, idx = parse_length_delimited(subdata, idx)
            header["gtfs_realtime_version"] = raw_bytes.decode("utf-8")

        elif field_num == 3 and wire_type == VARINT:
            # e.g. 1734835126
            val, idx = parse_varint(subdata, idx)
            header["timestamp"] = val

        elif field_num == 1001 and wire_type == LENGTH_DELIMITED:
            # This is a NYCT extension block. We'll skip or partially parse if desired.
            extension_bytes, idx = parse_length_delimited(subdata, idx)
            # For now, do nothing with the extension:
            # idx = skip_extension_fields(extension_bytes, 0) # or similar
        else:
            idx = skip_field(subdata, wire_type, idx)

    return header


# ------------------------------------------------------------
# PARSE ENTITY (top-level field_num=2 repeated)
# ------------------------------------------------------------
def parse_mta_entity(subdata):
    """
    Each entity has structure like:
      1: "1"   (ID string)
      2: 0     (int, often 0)
      3 { ... } (a sub-message with trip data)
      4 { ... } (maybe vehicle info or extension)

    We'll parse the ID, parse the #3 sub-message for trip updates/stops,
    and ignore #4 for now (or partially parse if needed).
    """
    idx = 0
    end = len(subdata)
    entity = {
        "id": None,
        "trip_update": None,
        "vehicle": None,  # or extension
    }

    while idx < end:
        field_num, wire_type, idx = parse_key(subdata, idx)

        if field_num == 1 and wire_type == LENGTH_DELIMITED:
            # e.g. "1", "2", "5" ...
            raw_bytes, idx = parse_length_delimited(subdata, idx)
            entity["id"] = raw_bytes.decode("utf-8")

        elif field_num == 3 and wire_type == LENGTH_DELIMITED:
            # The sub-message with trip/stop_time_updates
            trip_bytes, idx = parse_length_delimited(subdata, idx)
            entity["trip_update"] = parse_mta_trip_block(trip_bytes)

        elif field_num == 4 and wire_type == LENGTH_DELIMITED:
            # Possibly a vehicle or extension block
            # We skip or parse as needed:
            veh_bytes, idx = parse_length_delimited(subdata, idx)
            # entity["vehicle"] = parse_mta_vehicle(veh_bytes) # not implemented
        else:
            idx = skip_field(subdata, wire_type, idx)

    return entity


def parse_mta_trip_block(subdata):
    """
    The trip block, from your snippet, might look like:
       1 { 1: "128400_L..S", 5: "L", etc. } (Trip descriptor)
       2 { 1: 10, 4: "L14S", 2 { ... }, 3 { ... } } repeated stop_time_update
       4: 1734835126
       1001 { ... } (extension)
    We'll parse subfield #1 for trip descriptor,
    repeated subfield #2 for stop_time_update,
    skip the rest.
    """
    idx = 0
    end = len(subdata)
    trip_update = {"trip": None, "stop_time_update": []}

    while idx < end:
        field_num, wire_type, idx = parse_key(subdata, idx)

        if field_num == 1 and wire_type == LENGTH_DELIMITED:
            # sub-sub-message with trip descriptor
            tripdesc_bytes, idx = parse_length_delimited(subdata, idx)
            trip_update["trip"] = parse_mta_trip_descriptor(tripdesc_bytes)

        elif field_num == 2 and wire_type == LENGTH_DELIMITED:
            # repeated stop_time_update
            stu_bytes, idx_sub = parse_length_delimited(subdata, idx)
            idx = idx_sub
            stu_obj = parse_mta_stop_time_update(stu_bytes)
            trip_update["stop_time_update"].append(stu_obj)

        else:
            idx = skip_field(subdata, wire_type, idx)

    return trip_update


def parse_mta_trip_descriptor(subdata):
    """
    Example:
      1: "128400_L..S"
      5: "L"
      3: "20241221"
      ...
    We’ll just parse trip_id (field 1) and route_id (field 5).
    """
    idx = 0
    end = len(subdata)
    desc = {"trip_id": None, "route_id": None}

    while idx < end:
        field_num, wire_type, idx = parse_key(subdata, idx)

        if field_num == 1 and wire_type == LENGTH_DELIMITED:
            raw_bytes, idx = parse_length_delimited(subdata, idx)
            desc["trip_id"] = raw_bytes.decode("utf-8")

        elif field_num == 5 and wire_type == LENGTH_DELIMITED:
            raw_bytes, idx = parse_length_delimited(subdata, idx)
            desc["route_id"] = raw_bytes.decode("utf-8")
        else:
            idx = skip_field(subdata, wire_type, idx)

    return desc


def parse_mta_stop_time_update(subdata):
    """
    Example from snippet:
      1: 12
      4: "L16S"
      2 { 1: 0, 2: 1734835283, 3: 0 } (arrival)
      3 { 1: 0, 2: 1734835313, 3: 0 } (departure)
      5: 0
      1001 { ... }
    We parse 'stop_sequence' from field #1, 'stop_id' from field #4,
    arrival from field #2, departure from field #3.
    """
    idx = 0
    end = len(subdata)
    stu = {
        "stop_id": None,
        "stop_sequence": None,
        "arrival_time": None,
        "departure_time": None,
    }

    while idx < end:
        field_num, wire_type, idx = parse_key(subdata, idx)

        if field_num == 1 and wire_type == VARINT:
            # e.g. 12, 13, 14
            val, idx = parse_varint(subdata, idx)
            stu["stop_sequence"] = val

        elif field_num == 4 and wire_type == LENGTH_DELIMITED:
            # "L16S", "L14S", ...
            raw_bytes, idx = parse_length_delimited(subdata, idx)
            stu["stop_id"] = raw_bytes.decode("utf-8")

        elif field_num == 2 and wire_type == LENGTH_DELIMITED:
            # arrival sub-message
            arr_bytes, idx = parse_length_delimited(subdata, idx)
            stu["arrival_time"] = parse_mta_timestamp(arr_bytes)

        elif field_num == 3 and wire_type == LENGTH_DELIMITED:
            # departure sub-message
            dep_bytes, idx = parse_length_delimited(subdata, idx)
            stu["departure_time"] = parse_mta_timestamp(dep_bytes)

        else:
            idx = skip_field(subdata, wire_type, idx)

    return stu


def parse_mta_timestamp(subdata):
    """
    The arrival/departure is a sub-message like:
       1: 0
       2: 1734835283
       3: 0
    We only want the main time value from subfield #2.
    """
    idx = 0
    end = len(subdata)
    epoch_time = None

    while idx < end:
        field_num, wire_type, idx = parse_key(subdata, idx)
        if field_num == 2 and wire_type == VARINT:
            val, idx = parse_varint(subdata, idx)
            epoch_time = val
        else:
            idx = skip_field(subdata, wire_type, idx)

    return epoch_time


# ------------------------------------------------------------
# TOP-LEVEL: parse_feed_message
# ------------------------------------------------------------
def parse_feed_message(data):
    """
    Parse the top-level feed message for the MTA L-train data:

    Typically:
      1 { ... } => feed header
      2 { ... } => repeated entity blocks
      2 { ... }
      ...
    Returns a dict:
      {
        "header": {
           "gtfs_realtime_version": str or None,
           "timestamp": int (epoch) or 0
        },
        "entity": [
          {
            "id": str,
            "trip_update": {
               "trip": { "trip_id":..., "route_id":... },
               "stop_time_update": [
                 { "stop_id":..., "arrival_time":..., "departure_time":... }, ...
               ]
            },
            "vehicle": None or ...
          },
          ...
        ]
      }
    """

    idx = 0
    end = len(data)
    feedmsg = {
        "header": {
            "gtfs_realtime_version": None,
            "timestamp": 0,
        },
        "entity": [],
    }

    while idx < end:
        field_num, wire_type, idx = parse_key(data, idx)

        if field_num == 1 and wire_type == LENGTH_DELIMITED:
            # Header block
            sub_bytes, idx = parse_length_delimited(data, idx)
            feedmsg["header"] = parse_mta_header(sub_bytes)

        elif field_num == 2 and wire_type == LENGTH_DELIMITED:
            # Repeated entity
            sub_bytes, idx = parse_length_delimited(data, idx)
            entity_obj = parse_mta_entity(sub_bytes)
            feedmsg["entity"].append(entity_obj)

        else:
            idx = skip_field(data, wire_type, idx)

    return feedmsg
