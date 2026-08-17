# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
"""
Utility functions for looking up IUCN habitat classification codes from PostGIS raster tables.
"""

import logging

from django.db import connection

logger = logging.getLogger(__name__)


def get_iucn_habitat_codes(latitude, longitude):
    """
    Query the IUCN habit classification raster tables for the given coordinates.

    Args:
        latitude: Latitude in decimal degrees (WGS84)
        longitude: Longitude in decimal degrees (WGS84)

    Returns:
        dict with keys:
            - iucn_habitat_lvl1_code: Level 1 habitat code (int or None)
            - iucn_habitat_lvl2_code: Level 2 habitat code (int or None)
            - iucn_habitat_lvl1_name: Level 1 habitat name (str or None)
            - iucn_habitat_lvl2_name: Level 2 habitat name (str or None)
    """
    if latitude is None or longitude is None:
        return {
            "iucn_habitat_lvl1_code": None,
            "iucn_habitat_lvl2_code": None,
            "iucn_habitat_lvl1_name": None,
            "iucn_habitat_lvl2_name": None,
        }

    # Validate coordinates
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        logger.warning(f"Invalid coordinates for habitat lookup: ({latitude}, {longitude})")
        return {
            "iucn_habitat_lvl1_code": None,
            "iucn_habitat_lvl2_code": None,
            "iucn_habitat_lvl1_name": None,
            "iucn_habitat_lvl2_name": None,
        }

    result = {
        "iucn_habitat_lvl1_code": None,
        "iucn_habitat_lvl2_code": None,
        "iucn_habitat_lvl1_name": None,
        "iucn_habitat_lvl2_name": None,
    }

    try:
        with connection.cursor() as cursor:
            # Query Level 1 habitat classification
            cursor.execute(
                """
                SELECT ST_Value(rast, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) AS value
                FROM public.iucn_habitat_lvl1
                WHERE ST_Intersects(rast, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                LIMIT 1;
                """,
                [longitude, latitude, longitude, latitude],
            )

            row = cursor.fetchone()
            if row and row[0] is not None:
                lvl1_code = int(row[0])
                result["iucn_habitat_lvl1_code"] = lvl1_code
                result["iucn_habitat_lvl1_name"] = _get_level1_habitat_name(lvl1_code)

            # Query Level 2 habitat classification
            cursor.execute(
                """
                SELECT ST_Value(rast, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) AS value
                FROM public.iucn_habitat_lvl2
                WHERE ST_Intersects(rast, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                LIMIT 1;
                """,
                [longitude, latitude, longitude, latitude],
            )

            row = cursor.fetchone()
            if row and row[0] is not None:
                lvl2_code = int(row[0])
                result["iucn_habitat_lvl2_code"] = lvl2_code
                result["iucn_habitat_lvl2_name"] = _get_level2_habitat_name(lvl2_code)

        logger.info(
            f"IUCN habitat lookup for ({latitude}, {longitude}): "
            f"Level 1 = {result['iucn_habitat_lvl1_code']} ({result['iucn_habitat_lvl1_name']}), "
            f"Level 2 = {result['iucn_habitat_lvl2_code']} ({result['iucn_habitat_lvl2_name']})"
        )

    except Exception as e:
        logger.error(f"Error querying IUCN habitat for ({latitude}, {longitude}): {e}")

    return result


def _get_level1_habitat_name(code):
    """
    Get the human-readable name for a Level 1 IUCN habitat classification code.

    Args:
        code: Integer habitat code

    Returns:
        Human-readable habitat name string
    """
    level1_names = {
        0: "NoData/Ocean",
        100: "Forest - Boreal",
        200: "Forest - Subarctic",
        300: "Forest - Subantarctic",
        400: "Forest - Temperate",
        500: "Forest - Subtropical/Tropical Moist Lowland",
        600: "Forest - Subtropical/Tropical Mangrove",
        800: "Grassland",
        1400: "Wetlands (inland)",
    }

    return level1_names.get(code, f"Unknown Level 1 Code: {code}")


def _get_level2_habitat_name(code):
    """
    Get the human-readable name for a Level 2 IUCN habitat classification code.

    Level 2 codes are more granular variants of Level 1 codes.
    For example, 404 is a specific type of Temperate Forest (400 series).

    Args:
        code: Integer habitat code

    Returns:
        Human-readable habitat name string
    """
    # Level 2 codes are detailed versions of Level 1
    # Decode by getting the major category (first 1-2 digits * 100)
    if code == 0:
        return "NoData/Ocean"

    # Get the Level 1 base code (e.g., 404 -> 400, 1405 -> 1400)
    base_code = (code // 100) * 100
    base_name = _get_level1_habitat_name(base_code)

    # Return a more detailed description including the specific subcode
    return f"{base_name} (code: {code})"
