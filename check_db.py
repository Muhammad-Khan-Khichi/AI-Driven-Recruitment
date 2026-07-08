import requests
import sqlite3

EMAIL = "admin@admin.com"
USERNAME = "admin"
PASSWORD = "admin1234"

# 1. Register a new user
r = requests.post("http://localhost:8000/api/auth/signup", json={
    "email": EMAIL,
    "username": USERNAME,
    "password": PASSWORD,
    "full_name": "Admin User",
    "location": "Lahore"
})
print("Register:", r.status_code, r.json())

# 2. Promote to admin in the database
conn = sqlite3.connect("/tmp/app.db")
cursor = conn.cursor()
cursor.execute("UPDATE users SET is_admin = 1 WHERE email = ?", (EMAIL,))
conn.commit()

# 3. Verify
cursor.execute("SELECT id, username, email, is_admin FROM users WHERE email = ?", (EMAIL,))
print("User in DB:", cursor.fetchall())
conn.close()

# 4. Login (use username + password)
r = requests.post("http://localhost:8000/api/auth/login", json={
    "username": USERNAME,
    "password": PASSWORD
})
print("Login:", r.status_code, r.json())