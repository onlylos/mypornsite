import os
from flask import Flask, render_template, redirect, url_for, request, session
import stripe
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_secret_key")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID_BASIC = os.getenv("STRIPE_PRICE_ID_BASIC")

@app.route("/")
def age_verification():
    return render_template("verify_age.html")

@app.route("/set-age-verified", methods=["POST"])
def set_age_verified():
    session["age_verified"] = True
    return redirect(url_for("index"))

@app.route("/home")
def index():
    if not session.get("age_verified"):
        return redirect(url_for("age_verification"))
    return render_template("index.html")

@app.route("/subscribe/basic")
def subscribe_basic():
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[{
                'price': STRIPE_PRICE_ID_BASIC,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('success', _external=True),
            cancel_url=url_for('cancel', _external=True),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return str(e)

@app.route("/success")
def success():
    return render_template("success.html")

@app.route("/cancel")
def cancel():
    return render_template("cancel.html")

if __name__ == "__main__":
    app.run(debug=True)
