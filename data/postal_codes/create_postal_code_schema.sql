-- Postal Code PostgreSQL Schema with PostGIS Integration
-- Based on http://download.geonames.org/export/zip/readme.txt
-- Data source: GeoNames postal code database for US and Canada

-- Drop existing table if it exists
DROP TABLE IF EXISTS postal_codes CASCADE;

-- Main postal_codes table
CREATE TABLE postal_codes (
    id              SERIAL PRIMARY KEY,
    country         CHAR(2) NOT NULL,
    postal_code     VARCHAR(20) NOT NULL,
    place_name      VARCHAR(180),
    admin1_name     VARCHAR(100),
    admin1_code     VARCHAR(20),
    admin2_name     VARCHAR(100),
    admin2_code     VARCHAR(20),
    admin3_name     VARCHAR(100),
    admin3_code     VARCHAR(20),
    latitude        DECIMAL(10,7) NOT NULL,
    longitude       DECIMAL(10,7) NOT NULL,
    accuracy        SMALLINT
);

-- Add PostGIS geometry column for centroid
SELECT AddGeometryColumn('postal_codes', 'geom', 4326, 'POINT', 2);

-- Add PostGIS geometry column for boundary polygon
SELECT AddGeometryColumn('postal_codes', 'boundary', 4326, 'MULTIPOLYGON', 2);

-- Note: No unique constraint on (country, postal_code) because some ZIP codes
-- serve multiple places (e.g., military bases, remote areas)

-- Indexes for performance
CREATE INDEX idx_postal_codes_postal_code ON postal_codes(postal_code);
CREATE INDEX idx_postal_codes_country_postal_code ON postal_codes(country, postal_code);
CREATE INDEX idx_postal_codes_country_admin1 ON postal_codes(country, admin1_code);
CREATE INDEX idx_postal_codes_place_name ON postal_codes(place_name);
CREATE INDEX idx_postal_codes_geom ON postal_codes USING GIST(geom);
CREATE INDEX idx_postal_codes_boundary ON postal_codes USING GIST(boundary);

COMMENT ON TABLE postal_codes IS 'North American postal codes (US ZIP + Canada postal codes) with centroid coordinates';
COMMENT ON COLUMN postal_codes.postal_code IS 'Postal code (US: 5-digit ZIP or ZIP+4, CA: A1A 1A1 format)';
COMMENT ON COLUMN postal_codes.place_name IS 'City or place name associated with postal code';
COMMENT ON COLUMN postal_codes.admin1_code IS 'State/province code';
COMMENT ON COLUMN postal_codes.latitude IS 'Latitude of postal code centroid';
COMMENT ON COLUMN postal_codes.longitude IS 'Longitude of postal code centroid';
COMMENT ON COLUMN postal_codes.accuracy IS 'Coordinate accuracy: 1=estimated, 6=centroid';
COMMENT ON COLUMN postal_codes.geom IS 'PostGIS Point geometry for centroid (WGS84)';
COMMENT ON COLUMN postal_codes.boundary IS 'PostGIS MultiPolygon for ZIP/postal code boundaries (populate from Census/StatCan data)';
