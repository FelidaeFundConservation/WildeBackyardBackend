"""
Geographic utility functions for location privacy handling
"""

import math
import random

# Center of the Continental United States (near Lebanon, Kansas)
CONTINENTAL_US_CENTER_LAT = 39.8283
CONTINENTAL_US_CENTER_LON = -98.5795


def calculate_offset_coordinates(latitude, longitude, offset_km):
    """
    Calculate randomly offset coordinates from a given point.

    Args:
        latitude: Original latitude
        longitude: Original longitude
        offset_km: Maximum offset distance in kilometers

    Returns:
        tuple: (offset_latitude, offset_longitude)
    """
    if latitude is None or longitude is None or offset_km is None:
        return None, None

    # Convert offset from kilometers to degrees (approximate)
    # 1 degree of latitude ≈ 111 km
    # 1 degree of longitude varies by latitude

    # Random angle in radians
    angle = random.uniform(0, 2 * math.pi)

    # Random distance up to the maximum offset (in km)
    distance = random.uniform(0, offset_km)

    # Calculate offset in degrees
    # Latitude offset is straightforward
    lat_offset = (distance / 111.0) * math.cos(angle)

    # Longitude offset needs to account for latitude
    # At the equator, 1 degree longitude ≈ 111 km
    # At other latitudes, it's 111 * cos(latitude)
    lon_offset = (distance / (111.0 * math.cos(math.radians(latitude)))) * math.sin(
        angle
    )

    offset_latitude = latitude + lat_offset
    offset_longitude = longitude + lon_offset

    # Ensure latitude stays in valid range [-90, 90]
    offset_latitude = max(-90, min(90, offset_latitude))

    # Ensure longitude stays in valid range [-180, 180]
    if offset_longitude > 180:
        offset_longitude -= 360
    elif offset_longitude < -180:
        offset_longitude += 360

    return offset_latitude, offset_longitude


def get_continental_us_center():
    """
    Get the coordinates of the center of the continental United States.

    Returns:
        tuple: (latitude, longitude) of the center of continental US
    """
    return CONTINENTAL_US_CENTER_LAT, CONTINENTAL_US_CENTER_LON
