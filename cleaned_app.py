
import os
from flask import Flask, render_template, request, redirect, url_for
from flask_mail import Mail, Message
import stripe
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASS")
mail = Mail(app)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@app.route("/verify")
def age_verify():
    return render_template("age_verify.html")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/subscribe/<tier>")
def subscribe(tier):
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': 'price_id_for_' + tier,
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('success', _external=True),
            cancel_url=url_for('index', _external=True),
            metadata={'tier': tier}
        )
        return redirect(checkout_session.url)
    except Exception as e:
        return str(e), 500

@app.route("/success")
def success():
    return render_template("success.html")
