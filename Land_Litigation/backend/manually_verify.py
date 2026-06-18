import pymysql

def verify_user(phone):
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="Kaushika@2510",
        database="239_land_litigation_database_233"
    )
    with conn.cursor() as cursor:
        cursor.execute("UPDATE users SET is_verified=1 WHERE phone=%s", (phone,))
    conn.commit()
    conn.close()
    print(f"User with phone {phone} is now verified.")

if __name__ == "__main__":
    verify_user("9747393352")
