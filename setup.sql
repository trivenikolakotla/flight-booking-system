DROP DATABASE IF EXISTS flight_booking_db;
CREATE DATABASE flight_booking_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE flight_booking_db;

CREATE TABLE users (
    user_id    INT PRIMARY KEY AUTO_INCREMENT,
    name       VARCHAR(100) NOT NULL,
    email      VARCHAR(100) UNIQUE NOT NULL,
    password   VARCHAR(100) NOT NULL,
    role       ENUM('admin','user') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE airlines (
    airline_id  INT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL,
    country     VARCHAR(100) NOT NULL,
    code        VARCHAR(10)  NOT NULL,
    logo_color  VARCHAR(20)  DEFAULT '#1a237e',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE flights (
    flight_id        INT PRIMARY KEY AUTO_INCREMENT,
    airline_id       INT NOT NULL,
    departure        VARCHAR(100) NOT NULL,
    arrival          VARCHAR(100) NOT NULL,
    departure_time   DATETIME NOT NULL,
    arrival_time     DATETIME NOT NULL,
    status           VARCHAR(50) DEFAULT 'On-time',
    total_seats      INT DEFAULT 180,
    available_seats  INT DEFAULT 180,
    price            DECIMAL(10,2) DEFAULT 2999.00,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (airline_id) REFERENCES airlines(airline_id) ON DELETE CASCADE
);

CREATE TABLE customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id     INT,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(100) UNIQUE NOT NULL,
    phone       VARCHAR(20),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE bookings (
    booking_id  INT PRIMARY KEY AUTO_INCREMENT,
    flight_id   INT NOT NULL,
    customer_id INT NOT NULL,
    seats       INT DEFAULT 1,
    total_price DECIMAL(10,2) DEFAULT 0,
    status      VARCHAR(50) DEFAULT 'Confirmed',
    booked_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (flight_id)   REFERENCES flights(flight_id)   ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- ── Users (admin + demo user) ─────────────────────────────────────
-- passwords stored as plain text for simplicity (admin123, user123)
INSERT INTO users (name, email, password, role) VALUES
('Admin',       'admin@skybook.com', 'admin123', 'admin'),
('Ravi Kumar',  'ravi@skybook.com',  'user123',  'user'),
('Priya Sharma','priya@skybook.com', 'user123',  'user');

-- ── Airlines ──────────────────────────────────────────────────────
INSERT INTO airlines (name, country, code, logo_color) VALUES
('Air India',  'India', 'AI',  '#E31837'),
('IndiGo',     'India', '6E',  '#1A3C8F'),
('SpiceJet',   'India', 'SG',  '#E0392B'),
('Vistara',    'India', 'UK',  '#5C2D91'),
('GoAir',      'India', 'G8',  '#FF6600');

-- ── Flights ───────────────────────────────────────────────────────
INSERT INTO flights (airline_id, departure, arrival, departure_time, arrival_time, status, total_seats, available_seats, price) VALUES
(1, 'Delhi',     'Mumbai',    '2026-04-15 06:00:00', '2026-04-15 08:00:00', 'On-time', 180, 45,  3499),
(2, 'Mumbai',    'Bangalore', '2026-04-15 09:00:00', '2026-04-15 11:00:00', 'On-time', 180, 120, 2799),
(3, 'Hyderabad', 'Chennai',   '2026-04-15 12:00:00', '2026-04-15 13:30:00', 'On-time', 180, 80,  1999),
(4, 'Delhi',     'Kolkata',   '2026-04-15 14:00:00', '2026-04-15 16:30:00', 'Delayed', 180, 30,  4199),
(1, 'Bangalore', 'Delhi',     '2026-04-15 17:00:00', '2026-04-15 19:30:00', 'On-time', 180, 95,  3299),
(2, 'Chennai',   'Mumbai',    '2026-04-16 07:30:00', '2026-04-16 09:30:00', 'On-time', 180, 140, 2499),
(5, 'Kolkata',   'Delhi',     '2026-04-16 10:00:00', '2026-04-16 12:30:00', 'On-time', 180, 60,  3799),
(3, 'Mumbai',    'Hyderabad', '2026-04-16 13:00:00', '2026-04-16 14:30:00', 'On-time', 180, 110, 2199);

-- ── Customers ─────────────────────────────────────────────────────
INSERT INTO customers (user_id, name, email, phone) VALUES
(2, 'Ravi Kumar',   'ravi@skybook.com',  '9876543210'),
(3, 'Priya Sharma', 'priya@skybook.com', '9123456789'),
(NULL, 'Amit Singh','amit@example.com',  '9988776655');

-- ── Bookings ──────────────────────────────────────────────────────
INSERT INTO bookings (flight_id, customer_id, seats, total_price, status) VALUES
(1, 1, 2, 6998,  'Confirmed'),
(2, 2, 1, 2799,  'Confirmed'),
(3, 3, 3, 5997,  'Confirmed'),
(4, 1, 1, 4199,  'Cancelled');
