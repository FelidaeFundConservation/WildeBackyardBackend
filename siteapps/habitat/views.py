"""API views for querying IUCN habitat classification by coordinates."""

from django.contrib.gis.geos import Point
from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class HabitatTypeByCoordinateView(APIView):
    """
    Query IUCN habitat classification for a given lat/lon coordinate.

    GET /v1/habitat/api/query/?lat=37.7749&lon=-122.4194

    Returns both Level 1 (broad) and Level 2 (detailed) habitat classifications.
    """

    def get(self, request):
        """Query habitat type for given coordinates."""
        try:
            lat = float(request.GET.get("lat"))
            lon = float(request.GET.get("lon"))
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid coordinates. Provide lat and lon as numbers."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate coordinate bounds
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return Response(
                {"error": "Coordinates out of bounds. Lat must be -90 to 90, Lon must be -180 to 180."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create a point geometry (ST_Point expects lon, lat order)
        point_wkt = f"POINT({lon} {lat})"

        # Query both level 1 and level 2 rasters
        with connection.cursor() as cursor:
            # Query level 1 habitat
            cursor.execute(
                """
                SELECT ST_Value(rast, ST_SetSRID(ST_GeomFromText(%s), 4326)) AS habitat_lvl1
                FROM iucn_habitat_lvl1
                WHERE ST_Intersects(rast, ST_SetSRID(ST_GeomFromText(%s), 4326))
                LIMIT 1
            """,
                [point_wkt, point_wkt],
            )

            lvl1_result = cursor.fetchone()
            lvl1_value = int(lvl1_result[0]) if lvl1_result and lvl1_result[0] is not None else None

            # Query level 2 habitat
            cursor.execute(
                """
                SELECT ST_Value(rast, ST_SetSRID(ST_GeomFromText(%s), 4326)) AS habitat_lvl2
                FROM iucn_habitat_lvl2
                WHERE ST_Intersects(rast, ST_SetSRID(ST_GeomFromText(%s), 4326))
                LIMIT 1
            """,
                [point_wkt, point_wkt],
            )

            lvl2_result = cursor.fetchone()
            lvl2_value = int(lvl2_result[0]) if lvl2_result and lvl2_result[0] is not None else None

        # Map habitat codes to names (based on IUCN classification scheme)
        habitat_data = {
            "latitude": lat,
            "longitude": lon,
            "habitatLevel1": {
                "code": lvl1_value,
                "name": self._get_habitat_level1_name(lvl1_value) if lvl1_value else None,
            },
            "habitatLevel2": {
                "code": lvl2_value,
                "name": self._get_habitat_level2_name(lvl2_value) if lvl2_value else None,
            },
        }

        if lvl1_value is None and lvl2_value is None:
            habitat_data["message"] = "No habitat data available for this location (may be ocean or no data)"

        return Response(habitat_data, status=status.HTTP_200_OK)

    def _get_habitat_level1_name(self, code):
        """Map level 1 habitat code to name.

        Based on official IUCN habitat classification scheme codes
        from iucn_habitatclassification_composite_lvl1_ver003.tif
        """
        level1_names = {
            0: "Water",
            100: "Forest",
            200: "Savanna",
            300: "Shrubland",
            400: "Grassland",
            500: "Wetlands (inland)",
            600: "Rocky Areas",
            800: "Desert",
            1400: "Artificial - Terrestrial",
            1700: "Unknown",
        }
        return level1_names.get(code, f"Unknown habitat code ({code})")

    def _get_habitat_level2_name(self, code):
        """Map level 2 habitat code to name.

        Based on official IUCN habitat classification scheme codes
        from iucn_habitatclassification_composite_lvl2_ver003.tif
        """
        level2_names = {
            0: "Water",
            100: "Forest",
            101: "Forest - Boreal",
            102: "Forest - Subarctic",
            103: "Forest - Subantarctic",
            104: "Forest - Temperate",
            105: "Forest - Subtropical-tropical dry",
            106: "Forest - Subtropical-tropical moist lowland",
            107: "Forest - Subtropical-tropical mangrove vegetation",
            108: "Forest - Subtropical-tropical swamp",
            109: "Forest - Subtropical-tropical moist montane",
            200: "Savanna",
            201: "Savanna - Dry",
            202: "Savanna - Moist",
            300: "Shrubland",
            301: "Shrubland - Subarctic",
            302: "Shrubland - Subantarctic",
            303: "Shrubland - Boreal",
            304: "Shrubland - Temperate",
            305: "Shrubland - Subtropical-tropical dry",
            306: "Shrubland - Subtropical-tropical moist",
            307: "Shrubland - Subtropical-tropical high altitude",
            308: "Shrubland - Mediterranean-type",
            400: "Grassland",
            401: "Grassland - Tundra",
            402: "Grassland - Subarctic",
            403: "Grassland - Subantarctic",
            404: "Grassland - Temperate",
            405: "Grassland - Subtropical-tropical dry",
            406: "Grassland - Subtropical-tropical seasonally wet or flooded",
            407: "Grassland - Subtropical-tropical high altitude",
            500: "Wetlands (inland)",
            501: "Wetlands (inland) - Permanent rivers streams creeks",
            502: "Wetlands (inland) - Seasonal/intermittent/irregular rivers/streams/creeks",
            503: "Wetlands (inland) - Shrub dominated wetlands",
            504: "Wetlands (inland) - Bogs/marshes/swamps/fens/peatlands",
            505: "Wetlands (inland) - Permanent freshwater lakes",
            506: "Wetlands (inland) - Seasonal/intermittent freshwater lakes (over 8 ha)",
            507: "Wetlands (inland) - Permanent freshwater marshes/pools (under 8 ha)",
            508: "Wetlands (inland) - Seasonal/intermittent freshwater marshes/pools (under 8 ha)",
            509: "Wetlands (inland) - Freshwater springs and oases",
            510: "Wetlands (inland) - Tundra wetlands",
            511: "Wetlands (inland) - Alpine wetlands",
            512: "Wetlands (inland) - Geothermal wetlands",
            513: "Wetlands (inland) - Permanent inland deltas",
            514: "Wetlands (inland) - Permanent saline brackish or alkaline lakes",
            515: "Wetlands (inland) - Seasonal/intermittent saline brackish or alkaline lakes and flats",
            516: "Wetlands (inland) - Permanent /saline / brackish or alkaline marshes/pools",
            517: "Wetlands (inland) - Seasonal/intermittent /saline / brackish or alkaline marshes/pools",
            518: "Wetlands (inland) / Karst and other subterranean hydrological systems",
            600: "Rocky Areas",
            800: "Desert",
            801: "Desert - Hot",
            802: "Desert - Temperate",
            803: "Desert - Cold",
            1400: "Artificial - Terrestrial",
            1401: "Arable land",
            1402: "Pastureland",
            1403: "Plantations",
            1404: "Rural Gardens",
            1405: "Urban Areas",
            1406: "Subtropical/Tropical Heavily Degraded Former Forest",
            1700: "Unknown",
        }
        return level2_names.get(code, f"Unknown habitat code ({code})")
