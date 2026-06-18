import pymysql

def seed_history():
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="Kaushika@2510",
        database="239_land_litigation_database_233"
    )
    cursor = conn.cursor()

    # Pre-defined professional history data for 50 lands (No Randomization)
    history_data = []
    
    # List of realistic legal owner names
    first_owners = ["A. Ranganathan", "S. Venkat", "K. Natarajan", "M. Palanisamy", "R. Krishnan"]
    second_owners = ["V. Selvam", "T. Rajkumar", "N. Karthikeyan", "G. Balaji", "P. Sunder"]
    third_owners = ["D. Dinesh", "B. Ramesh", "S. Kannan", "M. Prabhu", "K. Ashok"]

    # Generate fixed, non-random, realistic sequence data for L001 to L050
    for i in range(1, 51):
        land_id = f"L{i:03d}"
        
        # 3 transfers for each land with fixed logical chronological dates
        history_data.append((land_id, first_owners[i % 5], "1992-04-15"))
        history_data.append((land_id, second_owners[i % 5], "2005-08-22"))
        history_data.append((land_id, third_owners[i % 5], "2018-11-05"))

    try:
        cursor.execute("TRUNCATE TABLE land_history")
        
        for land_id, owner_name, transfer_date in history_data:
            cursor.execute("""
                INSERT INTO land_history (land_id, owner_name, transfer_date)
                VALUES (%s, %s, %s)
            """, (land_id, owner_name, transfer_date))
        
        conn.commit()
        print(f"Successfully added {len(history_data)} fixed, non-random historical records for 50 lands!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_history()
