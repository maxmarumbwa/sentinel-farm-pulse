-- Create the user
CREATE USER sentinel_user
WITH PASSWORD 'sentinel_password';

-- Create the database
CREATE DATABASE sentinel_farm
OWNER sentinel_user;

-- Connect to the database
\c sentinel_farm

-- Enable PostGIS
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;

-- (Optional but recommended)
CREATE EXTENSION fuzzystrmatch;
CREATE EXTENSION postgis_tiger_geocoder;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE sentinel_farm TO sentinel_user;
