import pymysql

conn = pymysql.connect(
    host="localhost",
    user="root",
    password="Kaushika@2510",
    database="239_land_litigation_database_233",
    cursorclass=pymysql.cursors.DictCursor
)

with conn.cursor() as cursor:
    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s", 
        ("monisha@gmail.com", "Jesus@123")
    )
    user = cursor.fetchone()
    print(user if user else "Not found")

conn.close()
