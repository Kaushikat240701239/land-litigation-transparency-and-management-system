import sqlite3
import os

db_path = os.path.join(r"c:\Land_Litigation\backend", "database.db")
conn = sqlite3.connect(db_path)
try:
    conn.execute("INSERT INTO users (name,email,password,phone,is_verified,role) VALUES ('Monisha','monisha@gmail.com','Jesus@123','9444043820',1,'farmer')")
except sqlite3.IntegrityError:
    pass
conn.commit()
conn.close()
print("Done")
