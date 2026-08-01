"""API views for querying IUCN habitat classification and GeoNames place data."""

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


class NearestPlaceView(APIView):
    """
    Find the nearest place name for given coordinates.

    GET /v1/habitat/api/geonames/nearest/?lat=37.7749&lon=-122.4194&radius=50000

    Returns the nearest populated place with details including state/province.
    """

    def get(self, request):
        """Find nearest place to coordinates."""
        try:
            lat = float(request.GET.get("lat"))
            lon = float(request.GET.get("lon"))
            radius_meters = int(request.GET.get("radius", 50000))  # Default 50km
            limit = min(int(request.GET.get("limit", 1)), 10)  # Max 10 results
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid parameters. Provide lat, lon as numbers, optional radius (meters) and limit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate inputs
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return Response({"error": "Coordinates out of bounds."}, status=status.HTTP_400_BAD_REQUEST)

        if radius_meters > 500000:  # Max 500km
            radius_meters = 500000

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    g.geonameid,
                    g.name,
                    g.asciiname,
                    g.latitude,
                    g.longitude,
                    g.fclass,
                    g.fcode,
                    g.country,
                    g.admin1,
                    a.name as state_province,
                    g.population,
                    g.elevation,
                    g.timezone,
                    ST_Distance(
                        g.geom::geography,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    ) as distance_meters,
                    fc.name as feature_type
                FROM geonames g
                LEFT JOIN admin1_codes a ON (g.country || '.' || g.admin1 = a.code)
                LEFT JOIN feature_codes fc ON (g.fclass || '.' || g.fcode = fc.code)
                WHERE ST_DWithin(
                    g.geom::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                    %s
                )
                ORDER BY distance_meters, population DESC NULLS LAST
                LIMIT %s
                """,
                [lon, lat, lon, lat, radius_meters, limit],
            )

            places = []
            for row in cursor.fetchall():
                places.append(
                    {
                        "geonameid": row[0],
                        "name": row[1],
                        "asciiName": row[2],
                        "latitude": float(row[3]),
                        "longitude": float(row[4]),
                        "featureClass": row[5],
                        "featureCode": row[6],
                        "country": row[7],
                        "admin1Code": row[8],
                        "stateProvince": row[9],
                        "population": row[10],
                        "elevation": row[11],
                        "timezone": row[12],
                        "distanceMeters": round(row[13], 2),
                        "featureType": row[14],
                    }
                )

        if not places:
            return Response(
                {
                    "message": f"No places found within {radius_meters}m of coordinates",
                    "latitude": lat,
                    "longitude": lon,
                    "radiusMeters": radius_meters,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "latitude": lat,
                "longitude": lon,
                "radiusMeters": radius_meters,
                "places": places,
            },
            status=status.HTTP_200_OK,
        )


class SearchPlacesView(APIView):
    """
    Search for places by name.

    GET /v1/habitat/api/geonames/search/?name=San%20Francisco&country=US&limit=10

    Returns places matching the search criteria.
    """

    def get(self, request):
        """Search for places by name."""
        name = request.GET.get("name", "").strip()
        country = request.GET.get("country", "").upper()
        state = request.GET.get("state", "").strip()
        feature_class = request.GET.get("fclass", "").upper()
        limit = min(int(request.GET.get("limit", 10)), 100)  # Max 100 results

        if not name or len(name) < 2:
            return Response(
                {"error": "Name parameter required (minimum 2 characters)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build query dynamically
        query = """
            SELECT
                g.geonameid,
                g.name,
                g.asciiname,
                g.latitude,
                g.longitude,
                g.fclass,
                g.fcode,
                g.country,
                g.admin1,
                a.name as state_province,
                g.population,
                g.elevation,
                g.timezone,
                fc.name as feature_type
            FROM geonames g
            LEFT JOIN admin1_codes a ON (g.country || '.' || g.admin1 = a.code)
            LEFT JOIN feature_codes fc ON (g.fclass || '.' || g.fcode = fc.code)
            WHERE (g.name ILIKE %s OR g.asciiname ILIKE %s)
        """
        params = [f"%{name}%", f"%{name}%"]

        if country:
            query += " AND g.country = %s"
            params.append(country)

        if state:
            query += " AND g.admin1 = %s"
            params.append(state)

        if feature_class:
            query += " AND g.fclass = %s"
            params.append(feature_class)

        query += " ORDER BY g.population DESC NULLS LAST, g.name LIMIT %s"
        params.append(limit)

        with connection.cursor() as cursor:
            cursor.execute(query, params)

            places = []
            for row in cursor.fetchall():
                places.append(
                    {
                        "geonameid": row[0],
                        "name": row[1],
                        "asciiName": row[2],
                        "latitude": float(row[3]),
                        "longitude": float(row[4]),
                        "featureClass": row[5],
                        "featureCode": row[6],
                        "country": row[7],
                        "admin1Code": row[8],
                        "stateProvince": row[9],
                        "population": row[10],
                        "elevation": row[11],
                        "timezone": row[12],
                        "featureType": row[13],
                    }
                )

        return Response(
            {
                "query": {
                    "name": name,
                    "country": country or None,
                    "state": state or None,
                    "featureClass": feature_class or None,
                },
                "count": len(places),
                "places": places,
            },
            status=status.HTTP_200_OK,
        )


class PlaceDetailView(APIView):
    """
    Get detailed information for a specific place by geonameid.

    GET /v1/habitat/api/geonames/place/5391959/

    Returns full details for the specified place.
    """

    def get(self, request, geonameid):
        """Get place details by geonameid."""
        try:
            geonameid = int(geonameid)
        except ValueError:
            return Response(
                {"error": "Invalid geonameid. Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    g.geonameid,
                    g.name,
                    g.asciiname,
                    g.alternatenames,
                    g.latitude,
                    g.longitude,
                    g.fclass,
                    g.fcode,
                    g.country,
                    g.admin1,
                    g.admin2,
                    g.admin3,
                    g.admin4,
                    a.name as state_province,
                    g.population,
                    g.elevation,
                    g.gtopo30,
                    g.timezone,
                    g.moddate,
                    fc.name as feature_type,
                    fc.description as feature_description
                FROM geonames g
                LEFT JOIN admin1_codes a ON (g.country || '.' || g.admin1 = a.code)
                LEFT JOIN feature_codes fc ON (g.fclass || '.' || g.fcode = fc.code)
                WHERE g.geonameid = %s
                """,
                [geonameid],
            )

            row = cursor.fetchone()

        if not row:
            return Response(
                {"error": f"Place with geonameid {geonameid} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Parse alternate names (comma-separated)
        alternate_names = row[3].split(",") if row[3] else []

        place_data = {
            "geonameid": row[0],
            "name": row[1],
            "asciiName": row[2],
            "alternateNames": alternate_names[:10],  # Limit to 10 alternates
            "latitude": float(row[4]),
            "longitude": float(row[5]),
            "featureClass": row[6],
            "featureCode": row[7],
            "country": row[8],
            "admin1Code": row[9],
            "admin2Code": row[10],
            "admin3Code": row[11],
            "admin4Code": row[12],
            "stateProvince": row[13],
            "population": row[14],
            "elevation": row[15],
            "gtopo30": row[16],
            "timezone": row[17],
            "modificationDate": str(row[18]) if row[18] else None,
            "featureType": row[19],
            "featureDescription": row[20],
        }

        return Response(place_data, status=status.HTTP_200_OK)


class PostalCodeLookupView(APIView):
    """
    Look up a postal code and return its centroid coordinates.

    GET /v1/habitat/api/postalcode/lookup/?code=94102&country=US
    GET /v1/habitat/api/postalcode/lookup/?code=K1A0B1&country=CA

    Returns centroid coordinates and place information for the postal code.
    """

    def get(self, request):
        """Lookup postal code centroid."""
        postal_code = request.GET.get("code", "").strip().upper()
        country = request.GET.get("country", "US").strip().upper()

        if not postal_code:
            return Response(
                {"error": "Postal code required (parameter: code)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if country not in ["US", "CA"]:
            return Response(
                {"error": "Country must be US or CA"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # For US, normalize ZIP code (remove hyphen in ZIP+4)
        if country == "US":
            postal_code = postal_code.replace("-", "")[:5]  # Take first 5 digits

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    postal_code,
                    place_name,
                    admin1_name,
                    admin1_code,
                    admin2_name,
                    latitude,
                    longitude,
                    accuracy,
                    country,
                    ST_AsGeoJSON(boundary) as boundary_geojson
                FROM postal_codes
                WHERE postal_code = %s AND country = %s
                LIMIT 1
                """,
                [postal_code, country],
            )

            row = cursor.fetchone()

        if not row:
            return Response(
                {"error": f"Postal code {postal_code} not found in {country}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        postal_data = {
            "postalCode": row[0],
            "placeName": row[1],
            "state": row[2] or row[3],  # Use full name if available, else code
            "stateCode": row[3],
            "county": row[4],
            "centroid": {
                "latitude": float(row[5]),
                "longitude": float(row[6]),
            },
            "accuracy": row[7],
            "country": row[8],
        }

        # Add boundary GeoJSON if available
        if row[9]:
            import json

            postal_data["boundary"] = json.loads(row[9])

        return Response(postal_data, status=status.HTTP_200_OK)


class PostalCodeSearchView(APIView):
    """
    Search postal codes by place name or partial code.

    GET /v1/habitat/api/postalcode/search/?q=San%20Francisco&country=US&limit=10
    GET /v1/habitat/api/postalcode/search/?q=941&country=US&limit=10

    Returns matching postal codes with centroid coordinates.
    """

    def get(self, request):
        """Search postal codes."""
        query = request.GET.get("q", "").strip()
        country = request.GET.get("country", "").strip().upper()
        limit = min(int(request.GET.get("limit", 20)), 100)

        if not query or len(query) < 2:
            return Response(
                {"error": "Search query required (minimum 2 characters, parameter: q)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build dynamic query
        sql = """
            SELECT
                postal_code,
                place_name,
                admin1_name,
                admin1_code,
                admin2_name,
                latitude,
                longitude,
                country
            FROM postal_codes
            WHERE (place_name ILIKE %s OR postal_code ILIKE %s)
        """
        params = [f"%{query}%", f"{query}%"]

        if country:
            if country not in ["US", "CA"]:
                return Response(
                    {"error": "Country must be US or CA"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            sql += " AND country = %s"
            params.append(country)

        sql += " ORDER BY postal_code LIMIT %s"
        params.append(limit)

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "postalCode": row[0],
                    "placeName": row[1],
                    "state": row[2] or row[3],
                    "stateCode": row[3],
                    "county": row[4],
                    "centroid": {
                        "latitude": float(row[5]),
                        "longitude": float(row[6]),
                    },
                    "country": row[7],
                }
            )

        return Response(
            {
                "query": query,
                "country": country or "ALL",
                "count": len(results),
                "postalCodes": results,
            },
            status=status.HTTP_200_OK,
        )


class NearbyPostalCodesView(APIView):
    """
    Find postal codes near a coordinate within specified radius.

    GET /v1/habitat/api/postalcode/nearby/?lat=37.7749&lon=-122.4194&radius=5000&limit=10

    Returns postal codes sorted by distance from the coordinate.
    Radius is in meters (default 10km, max 50km).
    """

    def get(self, request):
        """Find nearby postal codes."""
        try:
            lat = float(request.GET.get("lat"))
            lon = float(request.GET.get("lon"))
        except (TypeError, ValueError):
            return Response(
                {"error": "Valid latitude and longitude required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return Response(
                {"error": "Coordinates out of bounds. Lat: -90 to 90, Lon: -180 to 180"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        radius = min(int(request.GET.get("radius", 10000)), 50000)  # Default 10km, max 50km
        limit = min(int(request.GET.get("limit", 10)), 50)
        country = request.GET.get("country", "").strip().upper()

        # Build query with geographic distance calculation
        sql = """
            SELECT
                postal_code,
                place_name,
                admin1_name,
                admin1_code,
                admin2_name,
                latitude,
                longitude,
                country,
                ST_Distance(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                ) as distance_meters
            FROM postal_codes
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                %s
            )
        """
        params = [lon, lat, lon, lat, radius]

        if country:
            if country not in ["US", "CA"]:
                return Response(
                    {"error": "Country must be US or CA"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            sql += " AND country = %s"
            params.append(country)

        sql += " ORDER BY distance_meters LIMIT %s"
        params.append(limit)

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "postalCode": row[0],
                    "placeName": row[1],
                    "state": row[2] or row[3],
                    "stateCode": row[3],
                    "county": row[4],
                    "centroid": {
                        "latitude": float(row[5]),
                        "longitude": float(row[6]),
                    },
                    "country": row[7],
                    "distanceMeters": round(float(row[8]), 2),
                }
            )

        return Response(
            {
                "latitude": lat,
                "longitude": lon,
                "radiusMeters": radius,
                "count": len(results),
                "postalCodes": results,
            },
            status=status.HTTP_200_OK,
        )
