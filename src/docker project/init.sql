create schema pasta_db;

CREATE TABLE pasta_db.storage_levels (
    id SERIAL PRIMARY KEY,               -- Unique identifier for each storage level
    type CHAR(1) NOT NULL CHECK (type IN ('A', 'B')),  -- Type can be 'A' or 'B'
    wet_type CHAR(5) NOT NULL CHECK (wet_type IN ('fresh', 'dry')),  -- Wet type can be 'fresh' or 'dry'
    level INT NOT NULL                   -- Level as an integer
);

INSERT INTO pasta_db.storage_levels (type, wet_type, level) VALUES
('A', 'fresh', 21),
('B', 'dry', 21),
('A', 'dry', 21),
('B', 'fresh', 21);


CREATE TABLE pasta_db.batches (
    id BIGINT PRIMARY KEY,               -- Unique identifier for each batch
    blade_type VARCHAR(1) NOT NULL CHECK (blade_type IN ('A', 'B')), -- Type of blade (A or B)
    isFresh BOOLEAN NOT NULL,            -- Indicates if the batch is fresh or dry
    productionDate TIMESTAMP NOT NULL,   -- Date of production
    inStock INT NOT NULL CHECK (inStock >= 0)  -- Amount in stock
);

INSERT INTO pasta_db.batches (id, blade_type, isFresh, productionDate, inStock) VALUES
(1, 'A', TRUE, NOW(), 10),
(2, 'A', FALSE, NOW(), 10),
(3, 'B', TRUE, NOW(), 10),
(4, 'B', FALSE, NOW(), 10),
(5, 'A', TRUE, NOW(), 10),
(6, 'A', FALSE, NOW(), 10),
(7, 'B', TRUE, NOW(), 10),
(8, 'B', FALSE, NOW(), 10),
(9, 'A', TRUE, NOW(), 10),
(10, 'A', FALSE, NOW(), 10);

