import csv
import random

def generate_phone():
    return f"9{random.randint(700000000, 999999999)}"

input_file = 'land_details.csv'
output_file = 'land_details_new.csv'

try:
    with open(input_file, 'r', newline='') as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames + ['owner_phone']
        
        with open(output_file, 'w', newline='') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in reader:
                row['owner_phone'] = generate_phone()
                writer.writerow(row)
    print("CSV updated with phone numbers successfully.")
except Exception as e:
    print(f"Error: {e}")
