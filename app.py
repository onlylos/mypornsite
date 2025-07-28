import os
import sqlite3
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, redirect, session, jsonify
from flask_mail import Mail, Message
from dotenv import load_dotenv
import stripe

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Stripe setup
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# Flask-Mail setup
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASS")
mail = Mail(app)

# SQLite setup
conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT, password TEXT, expires_at TEXT)''')
conn.commit()

@app.route("/")
def landing():
    return '''
    <head><link rel="stylesheet" href="/static/style.css"></head>
    <div class="overlay">
      <h1>18+ Age Verification</h1>
      <p>By entering this website, you confirm that you are at least 18 years old...</p>
      <a href="/home" class="button large-button">ENTER</a>
      <p><a href="https://www.netsafe.org.nz/" target="_blank">I disagree - Exit here</a></p>
    </div>
    '''

@app.route("/home")
def home():
    return '''
    <head><link rel="stylesheet" href="/static/style.css"></head>
    <div class="overlay">
      <h1>Choose your plan</h1>
      <div class="pricing-container two-cols">
        <div class="plan highlight">
          <div class="badge">MOST POPULAR</div>
          <h3>Monthly Access Plan</h3>
          <h2>$20 NZD/mo</h2>
          <ul>
            <li>✔ Full access to all content</li>
            <li>✔ Past, present, future videos</li>
          </ul>
          <a href="/subscribe/price_1Rph2QRzfEb0Epi7yUJdkRzc" class="btn">Buy now</a>
        </div>
        <div class="plan">
          <h3>💎 Lifetime Access 💎</h3>
          <h2>$150 NZD</h2>
          <ul>
            <li>✔ One-time payment</li>
            <li>✔ Lifetime access</li>
          </ul>
          <a href="/subscribe/price_1Rph4KRzfEb0Epi7nL5JnokW" class="btn">Buy now</a>
        </div>
      </div>
      <a href="/vault">Already have a password?</a>
    </div>
    '''

@app.route("/subscribe/<price_id>")
def subscribe(price_id):
    lifetime_price_id = "price_1Rph4KRzfEb0Epi7nL5JnokW"
    mode = "payment" if price_id == lifetime_price_id else "subscription"

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode=mode,
        line_items=[{'price': price_id, 'quantity': 1}],
        success_url='https://yourcustomdomain.com/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url='https://yourcustomdomain.com/cancel',
        metadata={"plan": "lifetime" if mode == "payment" else "monthly"}
    )
    return redirect(checkout_session.url)

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        return str(e), 400

    if event["type"] == "checkout.session.completed":
        session_data = event["data"]["object"]
        email = session_data["customer_details"]["email"]
        plan = session_data["metadata"].get("plan")

        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat() if plan == "monthly" else None
        password = secrets.token_urlsafe(10)

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password, expires_at) VALUES (?, ?, ?)", (email, password, expires_at))
        conn.commit()
        conn.close()

        # Email password
        try:
            msg = Message("Your Access Password", sender=os.getenv("EMAIL_USER"), recipients=[email])
            msg.body = f"Thanks for subscribing!\nYour password: {password}"
            mail.send(msg)
        except Exception as e:
            print(f"Email send failed: {e}")

        print(f"✅ Created password for: {email} -> {password}")

    return jsonify(success=True)

@app.route("/vault", methods=["GET", "POST"])
def vault():
    if request.method == 'POST':
        pw = request.form['password']
        c.execute("SELECT email, expires_at FROM users WHERE password = ?", (pw,))
        user = c.fetchone()

        if user:
            email, expires_at = user
            if expires_at and datetime.utcnow() > datetime.fromisoformat(expires_at):
                return "<div class='overlay'><p>Password expired. <a href='/vault'>Try again</a>.</p></div>"

            session['authenticated'] = True
            return redirect("/videos")

        return "<div class='overlay'><p>Invalid password. <a href='/vault'>Try again</a>.</p></div>"

    return '''
    <head><link rel="stylesheet" href="/static/style.css"></head>
    <div class="overlay">
      <h2>Enter Your Access Password</h2>
      <form method="POST">
          <input type="password" name="password" required>
          <button type="submit">Unlock Vault</button>
      </form>
    </div>
    '''

@app.route("/videos")
def videos():
    if not session.get("authenticated"):
        return redirect("/vault")
    return '''
    <head><link rel="stylesheet" href="/static/style.css"></head>
    <div class="overlay">
      <h2>Your Private Videos</h2>
      <video width="480" controls><source src="/static/video1.mp4" type="video/mp4"></video>
      <video width="480" controls><source src="/static/video2.mp4" type="video/mp4"></video>
      <p><a href="/home">Return Home</a></p>
    </div>
    '''

@app.route("/success")
def success():
    return '''
    <head><link rel="stylesheet" href="/static/style.css"></head>
    <div class="overlay"><h2>Success! Check your email for your password.</h2><a href='/vault'>Enter Vault</a></div>
    '''

@app.route("/cancel")
def cancel():
    return '''
    <head><link rel="stylesheet" href="/static/style.css"></head>
    <div class="overlay"><h2>Payment canceled.</h2><a href='/home'>Go Back</a></div>
    '''

@app.route("/test-email")
def test_email():
    try:
        msg = Message("Test Email", sender=os.getenv("EMAIL_USER"), recipients=[os.getenv("EMAIL_USER")])
        msg.body = "This is a test email from your Flask app."
        mail.send(msg)
        return "Test email sent!"
    except Exception as e:
        return f"Failed to send: {e}"

if __name__ == "__main__":
    app.run(debug=True)
