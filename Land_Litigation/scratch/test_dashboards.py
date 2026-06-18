import requests

s = requests.Session()

def test_login(email):
    print(f"Testing login for {email}")
    r = s.post("http://127.0.0.1:5000/login_user", data={"email": email, "password": "123"}, allow_redirects=False)
    loc = r.headers.get("Location")
    print("Redirect to:", loc)
    if loc:
        r2 = s.get("http://127.0.0.1:5000" + loc)
        print("Page response code:", r2.status_code)
        if r2.status_code == 500:
            print("ERROR on", loc, ">>>", r2.text[:200])
        return loc
    return None

test_login("admin@gmail.com")
print("\n--- Testing Admin Claims ---")
r = s.get("http://127.0.0.1:5000/admin_claims")
print("Admin Claims status:", r.status_code)

s = requests.Session()
test_login("monisha@gmail.com")

print("\n--- Testing User Route (My Lands) ---")
r = s.get("http://127.0.0.1:5000/my_lands")
print("My Lands status:", r.status_code)

print("\n--- Testing Land Details ---")
r = s.get("http://127.0.0.1:5000/land_details/L001")
print("Land Details status:", r.status_code)
if r.status_code == 500:
    print("ERROR >>>", r.text[:200])
