import pymysql
import csv
import os

def dump_table(cursor, table_name):
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    if not rows:
        print(f"Table {table_name} is empty.")
        return
        
    csv_file = f"{table_name}_dump.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        # Get headers from the first row's dictionary keys
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported {table_name} to {csv_file}")

def main():
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="Kaushika@2510",
        database="239_land_litigation_database_233",
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        for table in tables:
            # The key is usually something like 'Tables_in_239_land_litigation_database_233'
            table_name = list(table.values())[0]
            dump_table(cursor, table_name)
            
    conn.close()
    print("Database dump complete. You can view the CSV files in your editor!")

if __name__ == "__main__":
    main()
