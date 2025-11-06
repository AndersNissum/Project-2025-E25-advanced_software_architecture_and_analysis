create schema pasta_db;

CREATE TABLE pasta_db.storage_levels (
    id SERIAL PRIMARY KEY,               -- Unique identifier for each storage level
    type CHAR(1) NOT NULL CHECK (type IN ('A', 'B')),  -- Type can be 'A' or 'B'
    wet_type CHAR(5) NOT NULL CHECK (wet_type IN ('fresh', 'dry')),  -- Wet type can be 'fresh' or 'dry'
    level INT NOT NULL                   -- Level as an integer
);

INSERT INTO pasta_db.storage_levels (type, wet_type, level) VALUES
('A', 'fresh', 25),
('B', 'dry', 40),
('A', 'dry', 60),
('B', 'fresh', 75);
