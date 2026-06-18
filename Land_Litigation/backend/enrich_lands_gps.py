import csv
import os
import random

# District base coordinates (Latitude, Longitude)
DISTRICT_COORDS = {
    'Chennai': (13.0827, 80.2707),
    'Salem': (11.6643, 78.1460),
    'Madurai': (9.9252, 78.1198),
    'Trichy': (10.7905, 78.7047),
    'Coimbatore': (11.0168, 76.9558)
}

def generate_location(district):
    base_lat, base_lon = DISTRICT_COORDS.get(district, (13.0, 80.0))
    # Add small random jitter to spread the points around the district
    lat = base_lat + random.uniform(-0.1, 0.1)
    lon = base_lon + random.uniform(-0.1, 0.1)
    # Generate mock address
    street_num = random.randint(1, 100)
    address = f"{street_num} Main Road, {district} Rural, Tamil Nadu"
    return round(lat, 5), round(lon, 5), address

csv_path = os.path.join(r'C:\Land_Litigation\backend', 'land_details.csv')

# Read existing data
with open(csv_path, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

# Ensure new fields are added precisely
if 'address' not in fieldnames:
    fieldnames.extend(['address', 'latitude', 'longitude'])

for row in rows:
    district = row.get('district', 'Chennai')
    if not row.get('address') or not row.get('latitude'):
        lat, lon, address = generate_location(district)
        row['latitude'] = lat
        row['longitude'] = lon
        row['address'] = address

# Write it back
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("Coordinates and addresses successfully injected!")
