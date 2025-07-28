from datetime import datetime
import sqlite3

def check_password(email, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute("SELECT password, expires_at FROM users WHERE email = ?", (email,))
    row = c.fetchone()

    conn.close()

    if not row:
        return False, "User not found"

    stored_password, expires_at = row

    if stored_password != password:
        return False, "Incorrect password"

    if expires_at:
        expires_at_dt = datetime.fromisoformat(expires_at)
        if datetime.utcnow() > expires_at_dt:
            return False, "Password expired"

    return True, "Access granted"
