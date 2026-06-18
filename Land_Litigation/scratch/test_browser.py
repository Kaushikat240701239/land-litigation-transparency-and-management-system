import requests

s = requests.Session()
# Go to login
r = s.get("http://127.0.0.1:5000/login")
print("Login page status:", r.status_code)

# Try login
login_data = {
    "email": "monisha@gmail.com",
    "password": "Jesus@123"
}
r = s.post("http://127.0.0.1:5000/login_user", data=login_data, allow_redirects=False)
print("Post login status:", r.status_code)
print("Redirect to:", r.headers.get("Location"))

if r.status_code in (301, 302):
    r2 = s.get("http://127.0.0.1:5000" + r.headers.get("Location"))
    print("Redirected page:", r.headers.get("Location"))
    print("Final page response:", len(r2.text), "bytes")
    # Check flash messages in the final page
    if "Invalid" in r2.text:
        print("Flash Error Contains: Invalid")
    if "Please verify" in r2.text:
        print("Flash Error Contains: Please verify")
