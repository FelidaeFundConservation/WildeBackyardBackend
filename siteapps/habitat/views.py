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
        """Map level 1 habitat code to name."""
        # Based on IUCN habitat classification scheme
        # TODO: Complete this mapping based on actual codes in the raster
        level1_names = {
            1: "Forest",
            2: "Savanna",
            3: "Shrubland",
            4: "Grassland",
            5: "Wetlands",
            6: "Rocky areas",
            7: "Caves and subterranean habitats",
            8: "Desert",
            9: "Marine",
            10: "Artificial/Terrestrial",
            11: "Artificial/Aquatic",
            12: "Introduced vegetation",
            13: "Other",
        }
        return level1_names.get(code, f"Unknown ({code})")

    def _get_habitat_level2_name(self, code):
        """Map level 2 habitat code to name."""
        # TODO: Complete this mapping based on actual codes in the raster
        # Level 2 has many more subdivisions
        return f"Habitat code {code}"
