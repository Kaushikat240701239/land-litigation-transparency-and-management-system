import pymysql
import os

# Connect to MySQL Server
conn = pymysql.connect(
    host="localhost",
    user="root",
    password="Kaushika@2510"
)
cursor = conn.cursor()

# Create database if it doesn't exist
cursor.execute("CREATE DATABASE IF NOT EXISTS 239_land_litigation_database_233")
conn.select_db("239_land_litigation_database_233")

cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

# 👤 USERS
cursor.execute("DROP TABLE IF EXISTS users")
cursor.execute("""
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    password VARCHAR(255),
    phone VARCHAR(20) UNIQUE,
    is_verified BOOLEAN DEFAULT 0,
    role VARCHAR(50)
)
""")

# ⚖️ CASES
cursor.execute("DROP TABLE IF EXISTS cases")
cursor.execute("""
CREATE TABLE cases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    land_id VARCHAR(100),
    case_details TEXT,
    status VARCHAR(50)
)
""")

# 🏡 LANDS (Master Data from CSV)
cursor.execute("DROP TABLE IF EXISTS lands")
cursor.execute("""
CREATE TABLE lands (
    land_id VARCHAR(100) PRIMARY KEY,
    survey_number VARCHAR(100),
    current_owner VARCHAR(255),
    owner_phone VARCHAR(20),
    state VARCHAR(100),
    district VARCHAR(100),
    address TEXT,
    latitude REAL,
    longitude REAL
)
""")

# 🔗 USER LANDS MAPPING (The Portfolio Bridge)
cursor.execute("DROP TABLE IF EXISTS user_lands")
cursor.execute("""
CREATE TABLE user_lands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    land_id VARCHAR(100),
    document_path TEXT, -- Path to uploaded Patta/Chitta
    claim_status VARCHAR(50) DEFAULT 'pending', -- pending, verified, rejected
    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, land_id)
)
""")

# 📜 LAND HISTORY
cursor.execute("DROP TABLE IF EXISTS land_history")
cursor.execute("""
CREATE TABLE land_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    land_id VARCHAR(100),
    owner_name VARCHAR(255),
    transfer_date VARCHAR(50)
)
""")

# Setup default admin safely
cursor.execute("""
INSERT INTO users (name,email,password,phone,is_verified,role)
VALUES ('admin','admin@gmail.com','123','9000000000',1,'admin')
""")

cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

conn.commit()
conn.close()

print("Database Schema Updated with Identity Integrity Support for MySQL")