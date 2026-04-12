-- GeoNames PostgreSQL Schema with PostGIS Integration
-- Based on http://download.geonames.org/export/dump/readme.txt

-- Drop existing tables if they exist
DROP TABLE IF EXISTS geonames CASCADE;
DROP TABLE IF EXISTS admin1_codes CASCADE;
DROP TABLE IF EXISTS feature_codes CASCADE;

-- Main geonames table
CREATE TABLE geonames (
    geonameid   INTEGER PRIMARY KEY,
    name        VARCHAR(200),
    asciiname   VARCHAR(200),
    alternatenames VARCHAR(10000),
    latitude    DECIMAL(10,7),
    longitude   DECIMAL(10,7),
    fclass      CHAR(1),
    fcode       VARCHAR(10),
    country     CHAR(2),
    cc2         VARCHAR(200),
    admin1      VARCHAR(20),
    admin2      VARCHAR(80),
    admin3      VARCHAR(20),
    admin4      VARCHAR(20),
    population  BIGINT,
    elevation   INTEGER,
    gtopo30     INTEGER,
    timezone    VARCHAR(40),
    moddate     DATE
);

-- Add PostGIS geometry column
SELECT AddGeometryColumn('geonames', 'geom', 4326, 'POINT', 2);

-- Admin1 codes (states/provinces)
CREATE TABLE admin1_codes (
    code        VARCHAR(20) PRIMARY KEY,
    name        VARCHAR(200),
    name_ascii  VARCHAR(200),
    geonameid   INTEGER
);

-- Feature codes (classification of place types)
CREATE TABLE feature_codes (
    code        VARCHAR(10) PRIMARY KEY,
    name        VARCHAR(200),
    description TEXT
);

-- Indexes for performance
CREATE INDEX idx_geonames_name ON geonames(name);
CREATE INDEX idx_geonames_country ON geonames(country);
CREATE INDEX idx_geonames_admin1 ON geonames(admin1);
CREATE INDEX idx_geonames_fcode ON geonames(fcode);
CREATE INDEX idx_geonames_population ON geonames(population DESC);
CREATE INDEX idx_geonames_geom ON geonames USING GIST(geom);

-- Combined index for common queries
CREATE INDEX idx_geonames_country_admin1 ON geonames(country, admin1);
CREATE INDEX idx_geonames_country_fcode ON geonames(country, fcode);

COMMENT ON TABLE geonames IS 'GeoNames geographical database - North America';
COMMENT ON COLUMN geonames.geonameid IS 'Integer ID of record in geonames database';
COMMENT ON COLUMN geonames.name IS 'Name of geographical point (UTF8)';
COMMENT ON COLUMN geonames.asciiname IS 'Name in plain ASCII characters';
COMMENT ON COLUMN geonames.fclass IS 'Feature class (A=country, P=city, H=stream, etc)';
COMMENT ON COLUMN geonames.fcode IS 'Feature code (PPL=populated place, ADM1=state, etc)';
COMMENT ON COLUMN geonames.country IS 'ISO-3166 2-letter country code';
COMMENT ON COLUMN geonames.admin1 IS 'FIPS code for state/province';
COMMENT ON COLUMN geonames.population IS 'Population (0 if not applicable)';
COMMENT ON COLUMN geonames.geom IS 'PostGIS Point geometry in WGS84';
