import pymysql

conn = pymysql.connect(
    host="localhost",
    user="root",
    password="Kaushika@2510",
    database="239_land_litigation_database_233",
    cursorclass=pymysql.cursors.DictCursor
)

with conn.cursor() as cursor:
    cursor.execute("SELECT id, email, password, is_verified, phone FROM users")
    users = cursor.fetchall()
    for u in users:
        print(u)

conn.close()
