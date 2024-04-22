from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymongo
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash
import os
from dotenv import load_dotenv
import datetime
import secrets

load_dotenv(override=True)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Admin credentials
ADMIN_USERNAME = 'portal_admin1'
ADMIN_PASSWORD_HASH = generate_password_hash('Akfadmin01')

# Connect to MongoDB
try:
    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = cxn[os.getenv("MONGO_DBNAME")]
    cxn.admin.command("ping")
except ConnectionFailure as e:
    print("MongoDB connection failed: ", e)
    sys.exit(1)

@app.route("/")
def index():
    suggestions_list = list(db.suggestions.find({}).sort([("votes", pymongo.DESCENDING), ("created_at", pymongo.DESCENDING)]))
    return render_template("index.html", suggestions=suggestions_list)


@app.route("/suggest", methods=["GET", "POST"])
def suggest():
    if request.method == "POST":
        suggestion = {
            "title": request.form.get("title"),
            "description": request.form.get("description"),
            "votes": 0,
            "created_at": datetime.datetime.utcnow(),
            "status": "new"
        }
        db.suggestions.insert_one(suggestion)
        flash('Your suggestion has been added.')
        return redirect(url_for("index"))
    return render_template("suggest.html")

@app.route("/vote/<suggestion_id>")
def vote(suggestion_id):
    db.suggestions.update_one({"_id": ObjectId(suggestion_id)}, {"$inc": {"votes": 1}})
    flash('Your vote has been counted.')
    return redirect(url_for("index"))

@app.route("/login_admin", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_id"] = ADMIN_USERNAME
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin username and/or password")
    return render_template("login_admin.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        flash("Admin access required")
        return redirect(url_for("login_admin"))
    
    suggestions = db.suggestions.find({})
    return render_template("admin_dashboard.html", suggestions=suggestions)

@app.route("/edit_status/<suggestion_id>", methods=["GET", "POST"])
def edit_status(suggestion_id):
    if "admin_id" not in session:
        flash("Admin access required")
        return redirect(url_for("login_admin"))

    suggestion = db.suggestions.find_one({"_id": ObjectId(suggestion_id)})
    if not suggestion:
        flash("Suggestion not found")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        new_status = request.form.get("status")
        if new_status not in ["new", "acknowledged", "in progress", "implemented"]:
            flash("Invalid status")
            return redirect(url_for("admin_dashboard"))
        
        db.suggestions.update_one({"_id": ObjectId(suggestion_id)}, {"$set": {"status": new_status}})
        flash("Suggestion status updated")
        return redirect(url_for("admin_dashboard"))

@app.route("/delete_suggestion/<suggestion_id>", methods=["POST"])
def delete_suggestion(suggestion_id):
    if "admin_id" not in session:
        flash("Admin access required")
        return redirect(url_for("login_admin"))

    db.suggestions.delete_one({"_id": ObjectId(suggestion_id)})
    flash("Suggestion deleted successfully")
    return redirect(url_for("admin_dashboard"))

@app.route("/logout_admin")
def logout_admin():
    session.pop("admin_id", None)
    flash("You have been logged out.")
    return redirect(url_for("login_admin"))

if __name__ == "__main__":
    app.run(debug=True)

