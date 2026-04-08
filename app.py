from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import json, os, pandas as pd
import zipfile

from products import products
from nlp_engine import extract_price, intent
from negotiation_engine import negotiate

app = Flask(__name__)
app.secret_key = "secret123"

USERS_FILE = "users.json"
ORDERS_FILE = "orders.xlsx"

# ---------------- INIT FILES ----------------
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            users = json.load(open(USERS_FILE))
        except json.JSONDecodeError:
            users = {}

        username = request.form["username"]
        password = request.form["password"]

        if username in users and check_password_hash(users[username], password):
            session["user"] = username
            return redirect("/home")

        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try: 
            users = json.load(open(USERS_FILE))
        except json.JSONDecodeError:
            users = {}

        users[request.form["username"]] = generate_password_hash(
            request.form["password"]
        )
        json.dump(users, open(USERS_FILE, "w"))

        return redirect("/")

    return render_template("register.html")

# ---------------- HOME (AFTER LOGIN) ----------------
@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/")
    return render_template("home.html")

# ---------------- PRODUCTS ----------------
@app.route("/products")
def product_page():
    if "user" not in session:
        return redirect("/")
    return render_template("products.html", products=products)

# ---------------- CHAT ----------------
@app.route("/chat/<int:pid>")
def chat(pid):
    if "user" not in session:
        return redirect("/")

    session["pid"] = pid
    session["round"] = 1
    session["final_price"] = None

    return render_template("chat.html", product=products[pid - 1])

# ---------------- CHAT MESSAGE API ----------------
@app.route("/message", methods=["POST"])
def message():
    text = request.json["msg"].lower()
    product = products[session["pid"] - 1]

    # Greeting
    if intent(text) == "greet":
        return jsonify({
            "reply": product["conversation"]["welcome"] + " " +
                     product["conversation"]["ask_price"],
            "payment": False
        })

    # Accept deal
    if intent(text) == "accept" and session.get("final_price"):
        return jsonify({
            "reply": product["conversation"]["deal"] +
                     f" ✅ Final price ₹{session['final_price']}",
            "payment": True
        })

    # Price negotiation
    price = extract_price(text)
    if price:
        ok, value = negotiate(price, product, session["round"])
        session["round"] += 1
        session["final_price"] = value

        if ok:
            return jsonify({
                "reply": f"🎉 Deal confirmed at ₹{value}. Type 'ok deal' to continue.",
                "payment": False
            })

        return jsonify({
            "reply": product["conversation"]["after_offer"] +
                     f" Best I can offer is ₹{value}.",
            "payment": False
        })

    return jsonify({
        "reply": "Please enter a valid price or type 'ok deal'.",
        "payment": False
    })

# ---------------- PAYMENT ----------------
@app.route("/payment", methods=["GET", "POST"])
def payment():
    if "user" not in session or not session.get("final_price"):
        return redirect("/products")

    if request.method == "POST":
        data = {
            "User": session["user"],
            "Product": products[session["pid"] - 1]["name"],
            "Final Price": session["final_price"],
            "Payment Mode": request.form["payment"]
        }

        df = pd.DataFrame([data])

        if os.path.exists(ORDERS_FILE):
            try:
                old = pd.read_excel(ORDERS_FILE, engine="openpyxl")
                df = pd.concat([old, df], ignore_index=True)
            except (ValueError, FileNotFoundError, zipfile.BadZipFile):
                df = pd.DataFrame([data])

        df.to_excel(ORDERS_FILE, index=False, engine="openpyxl")

        # ❗ clear only order-related session, not user
        session.pop("pid", None)
        session.pop("round", None)
        session.pop("final_price", None)

        return redirect("/success")

    return render_template(
        "payment.html",
        product=products[session["pid"] - 1],
        price=session["final_price"]
    )

# ---------------- SUCCESS ----------------
@app.route("/success")
def success():
    if "user" not in session:
        return redirect("/")
    return render_template("success.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
