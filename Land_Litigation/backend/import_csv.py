import pymysql
import csv
import os

# Connect to MySQL Server
conn = pymysql.connect(
    host="localhost",
    user="root",
    password="Kaushika@2510",
    database="239_land_litigation_database_233"
)
cursor = conn.cursor()

csv_dir = os.path.dirname(os.path.abspath(__file__))

# Clear existing data for fresh sync
cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
cursor.execute("TRUNCATE TABLE lands")
cursor.execute("TRUNCATE TABLE cases")
cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

# Import land details
with open(os.path.join(csv_dir, 'land_details.csv'), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        lat = row.get('latitude')
        lon = row.get('longitude')
        lat = float(lat) if lat and lat.strip() else 0.0
        lon = float(lon) if lon and lon.strip() else 0.0
        
        cursor.execute("""
            REPLACE INTO lands (land_id, survey_number, current_owner, owner_phone, state, district, address, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (row['land_id'], row['survey_number'], row['owner_name'], row['owner_phone'], row['state'], row['district'], row.get('address', ''), lat, lon))

# Import case details
with open(os.path.join(csv_dir, 'case_details.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        case_details = f"{row['case_description']} (Court: {row['court_name']})" if row['court_name'] else row['case_description']
        status = row['case_status'].lower()
        cursor.execute("""
            INSERT INTO cases (land_id, case_details, status)
            VALUES (%s, %s, %s)
        """, (row['land_id'], case_details, status))

conn.commit()
conn.close()

print("Data with Phone Identity imported successfully!")