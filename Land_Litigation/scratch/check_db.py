import sqlite3
import os

db_paths = ["database.db", "backend/database.db"]

for db_path in db_paths:
    if os.path.exists(db_path):
        print(f"--- Checking {db_path} ---")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
            for table in tables:
                table_name = table[0]
                if table_name == 'sqlite_sequence': continue
                count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                print(f"Table {table_name}: {count} rows")
            conn.close()
        except Exception as e:
            print(f"Error checking {db_path}: {e}")
    else:
        print(f"File {db_path} does not exist.")
