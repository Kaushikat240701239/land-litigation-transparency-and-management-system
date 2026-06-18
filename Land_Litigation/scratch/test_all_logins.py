import requests

s = requests.Session()
def test_login(email, password):
    login_data = {
        "email": email,
        "password": password
    }
    r = s.post("http://127.0.0.1:5000/login_user", data=login_data, allow_redirects=False)
    print("Email:", email, "Status:", r.status_code)
    if r.status_code in (301, 302):
        loc = r.headers.get("Location")
        print(" Redirect to:", loc)
        r2 = s.get("http://127.0.0.1:5000" + loc)
        print("  Final page length:", len(r2.text), "Status:", r2.status_code)
        if r2.status_code == 500:
            print("  500 ERROR CONTENT:")
            print(r2.text[:500])

test_login("admin@gmail.com", "123")
test_login("landlitix@gmail.com", "123")
test_login("monisha@gmail.com", "Jesus@123")
