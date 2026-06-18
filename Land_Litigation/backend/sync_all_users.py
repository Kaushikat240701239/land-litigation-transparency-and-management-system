import pymysql

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="Kaushika@2510",
        database="239_land_litigation_database_233",
        cursorclass=pymysql.cursors.DictCursor
    )

def sync_user_lands(conn, user_id, phone):
    with conn.cursor() as cursor:
        cursor.execute("SELECT land_id FROM lands WHERE owner_phone=%s", (phone,))
        matching_lands = cursor.fetchall()
        count = 0
        for land in matching_lands:
            try:
                cursor.execute("""
                    INSERT IGNORE INTO user_lands (user_id, land_id, document_path, claim_status)
                    VALUES (%s, %s, %s, 'verified')
                """, (user_id, land['land_id'], 'System Verified via Phone'))
                count += 1
            except Exception as e:
                print(f"Sync error for user {user_id}: {e}")
        return count

def main():
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, name, phone FROM users WHERE is_verified=1")
        users = cursor.fetchall()
        
        total_synced = 0
        print(f"Checking {len(users)} verified users...")
        
        for user in users:
            count = sync_user_lands(conn, user['id'], user['phone'])
            if count > 0:
                print(f"Synced {count} lands for user: {user['name']} ({user['phone']})")
                total_synced += count
        
        conn.commit()
    conn.close()
    print(f"\nMigration Complete! Total lands automatically linked: {total_synced}")

if __name__ == "__main__":
    main()
