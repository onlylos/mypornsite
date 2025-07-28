import os
import random
import string
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, request, render_template, abort
from flask_mail import Mail, Message
from dotenv import load_dotenv
import stripe

# Load environment variables
load_dotenv()

# Stripe config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Flask app setup
app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASS")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("EMAIL_USER")

mail = Mail(app)

# SQLite setup
DB_FILE = "users.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                expires_at TEXT
            )
        ''')

init_db()

def generate_password(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def store_user(email, password, plan):
    expires_at = None
    if plan == 'monthly':
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("REPLACE INTO users (email, password, expires_at) VALUES (?, ?, ?)",
                     (email, password, expires_at))

def is_password_valid(password):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.execute("SELECT expires_at FROM users WHERE password = ?", (password,))
        row = cur.fetchone()
        if row:
            expires_at = row[0]
            if expires_at is None:
                return True
            return datetime.fromisoformat(expires_at) > datetime.now()
        return False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/vault")
def vault():
    return render_template("vault.html")

@app.route("/success")
def success():
    return render_template("success.html")

@app.route("/access", methods=["POST"])
def access():
    password = request.form.get("password")
    if is_password_valid(password):
        return render_template("videos.html")
    return render_template("vault.html", error="Invalid or expired password.")

@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('stripe-signature')
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        print("❌ Webhook signature verification failed:", e)
        return '', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session['customer_details']['email']
        mode = session.get("mode")
        password = generate_password()
        store_user(customer_email, password, "lifetime" if mode == "payment" else "monthly")

        # Send password email
        try:
            msg = Message("Your Access Password",
                          recipients=[customer_email])
            msg.body = f"""Thanks for subscribing!

Your password is:

{password}

Use it here: https://mypornsite.onrender.com/vault"""
            mail.send(msg)
            print(f"📬 Email sent to: {customer_email}")
        except Exception as e:
            print("❌ Failed to send email:", e)

    return '', 200

@app.route("/test-email")
def test_email():
    test_recipient = request.args.get("email", os.getenv("EMAIL_USER"))
    try:
        msg = Message("Test Email", recipients=[test_recipient])
        msg.body = "This is a test email from your Flask app."
        mail.send(msg)
        return "✅ Test email sent!"
    except Exception as e:
        print("❌ Email test failed:", e)
        return f"❌ Email test failed: {e}"

if __name__ == "__main__":
    app.run(debug=True)
