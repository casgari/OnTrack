import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash


from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached (adapted from finance)
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies) (adapted from finance)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///OnTrack.db")

# Loads homepage featuring runs of user's friends


@app.route("/")
@login_required
def index():
    runs = db.execute("SELECT * FROM runs WHERE user_id IN (SELECT friend_id FROM friends WHERE user_id = ?) OR user_id = ? ORDER BY year DESC, month DESC, day DESC",
                        session["user_id"], session["user_id"])
    return render_template("homepage.html", runs=runs)


# Upload runs to website
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    # Loads form to upload run
    if request.method == "GET":
        return render_template("upload.html")
    else:
        # Calculates pace per unit measurement
        total_sec = int(request.form.get("seconds")) + 60 * int(request.form.get("minutes")) + 3600 * int(request.form.get("hours"))
        distance = float(request.form.get("distance"))
        pace = int(total_sec / distance)
        pace_minutes = int(pace / 60)
        pace_seconds = int(pace - (pace_minutes * 60))
        
        name = db.execute("SELECT name FROM userinfo WHERE id = ?", session["user_id"])
        # Inserts run to runs table in database
        db.execute("INSERT INTO runs (user_id, distance, year, month, day, hours, minutes, seconds, measurement, name, pace_min, pace_sec) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    session["user_id"], distance, request.form.get("year"), request.form.get("month"), 
                    request.form.get("day"), request.form.get("hours"), request.form.get("minutes"), request.form.get("seconds"),
                    request.form.get("measurement"), name[0]["name"], pace_minutes, pace_seconds)
        flash("Uploaded!")
        return redirect("/")

# Calculator that predicts future race times based on past performances of varying distances


@app.route("/racecalculator", methods=["GET", "POST"])
@login_required
def racecalculator():
    # Loads calculator form
    if request.method == "GET":
        return render_template("runningcalc.html")
    else:
        # Checks if input left empty, defaulting to 0
        if not request.form.get("hours"):
            hours1 = 0
        else:
            hours1 = int(request.form.get("hours"))
        if not request.form.get("minutes"):
            minutes1 = 0
        else:
            minutes1 = int(request.form.get("minutes"))
        if not request.form.get("seconds"):
            seconds1 = 0
        else:
            seconds1 = int(request.form.get("seconds"))
        
        # Ensures valid distances were entered
        if float(request.form.get("distance")) <= 0:
            return apology("Enter a valid distance")
        elif float(request.form.get("predictdistance")) <= 0:
            return apology("Enter valid race distance")
            
        # Calculates total time in terms of seconds
        total_sec = seconds1 + 60 * minutes1 + 3600 * hours1
        
        # Converts all distances to miles
        if request.form.get("measurement") == "km":
            distance = float(request.form.get("distance")) * .621371
        else:
            distance = float(request.form.get("distance"))
        if request.form.get("measurement2") == "km":
            predicted_dist = float(request.form.get("predictdistance")) * .621371
        else:
            predicted_dist = float(request.form.get("predictdistance"))
        # Stores unaltered distance
        predictdistance = request.form.get("predictdistance")
        units = request.form.get("measurement2")
        # Prediciton calculation known as Reigel's formula:
        # Obtained from https://www.omnicalculator.com/sports/race-predictor
        predict_time = total_sec*((predicted_dist / distance)**1.06)
        
        # Calculates corresponding number of hours, minutes, seconds
        hours = int(predict_time / 3600)
        minutes = int((predict_time - (hours * 3600)) / 60)
        seconds = int(predict_time - (hours * 3600) - (minutes * 60))
        return render_template("racecalced.html", predictdistance=predictdistance, units=units, hours=hours, minutes=minutes, seconds=seconds)

# Calculator for running pace


@app.route("/pacecalc", methods=["GET", "POST"])
@login_required
def pacecalc():
    # Loads input form
    if request.method == "GET":
        return render_template("pacecalc.html")
    else:
        # Defaults empty inputs to 0
        if not request.form.get("hours"):
            hours1 = 0
        else:
            hours1 = int(request.form.get("hours"))
        if not request.form.get("minutes"):
            minutes1 = 0
        else:
            minutes1 = int(request.form.get("minutes"))
        if not request.form.get("seconds"):
            seconds1 = 0
        else:
            seconds1 = int(request.form.get("seconds"))
        # Ensures valid distance inputted
        if float(request.form.get("distance")) < 0:
            return apology("Enter valid distance ran")

        measurement = request.form.get("measurement")
        # Determines total time in terms of seconds
        total_sec = seconds1 + 60 * minutes1 + 3600 * hours1
        distance = float(request.form.get("distance"))
        
        # Calculates pace in terms of minutes & seconds
        pace = int(total_sec / distance)
        minutes = int(pace / 60)
        seconds = int(pace - (minutes * 60))
        return render_template("pacecalced.html", minutes=minutes, seconds=seconds, measurement=measurement)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in (adapted from finance) """

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user (adapted from finance)"""

    # Open registration page
    if request.method == "GET":
        return render_template("register.html")

    else:
        # Incorrect confirmation password
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Please ensure the passwords match")
        try:
            # Input username and password into database
            id = db.execute("INSERT INTO users (username, hash) VALUES(?, ?)",
                            request.form.get("username"),
                            generate_password_hash(request.form.get("password")))
        except RuntimeError:
            # Username already taken
            return apology("Username taken")
            
        # Log user in
        session["user_id"] = id
        
        # Update users personal info
        db.execute("INSERT INTO userinfo(id, name, age, weight, height_ft, gender, height_in) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    session["user_id"], request.form.get("name"), request.form.get("age"), request.form.get("weight"),
                    request.form.get("height_ft"), request.form.get("gender"), request.form.get("height_in"))
        flash("Registered!")
        return redirect("/")


# Display user's own running statistics
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    # Obtain running log
    runs = db.execute("SELECT * FROM runs WHERE user_id = ? ORDER BY year DESC, month DESC, day DESC", session["user_id"])
    # Obtain personal info
    profile_info = db.execute("SELECT * FROM userinfo WHERE id = ?", session["user_id"])
    return render_template("profile.html", runs=runs, profile_info=profile_info[0])


# Update user's personal information
@app.route("/updateprofile", methods=["GET", "POST"])
@login_required
def updateprofile():
    if request.method == "GET":
        # Retrieves user's previous data
        prev_info = db.execute("SELECT * FROM userinfo WHERE id = ?", session["user_id"])
        return render_template("updateprofile.html", prev_info=prev_info[0])

    else:
        # Updates information based on form
        db.execute("UPDATE userinfo SET id = ?, name = ?, age = ?, weight = ?, height_ft = ?, gender = ?, height_in = ?",
                    session["user_id"], request.form.get("name"), request.form.get("age"), request.form.get("weight"),
                    request.form.get("height_ft"), request.form.get("gender"), request.form.get("height_in"))
        flash("Profile Updated!")
        return redirect("/profile")


# Allow user to follow other friends
@app.route("/friends", methods=["GET", "POST"])
@login_required
def friends():
    # Load form to search for new friends and display current friends
    if request.method == "GET":
        friends = db.execute(
            "SELECT * FROM userinfo WHERE id IN (SELECT friend_id FROM friends WHERE user_id = ?)", session["user_id"])
        
        return render_template("friends.html", friends=friends)
    else:
        search = request.form.get("name")
        user_id = db.execute("SELECT id FROM users WHERE username = ?", search)
        # Determine if user exists
        if len(user_id) != 1:
            flash("No friend found")
            return redirect("/friends")
            
        # Determine if users are already friends
        already_friends = db.execute("SELECT * FROM friends WHERE user_id = ? AND friend_id = ?",
                                     session["user_id"], user_id[0]["id"])
        if len(already_friends) != 0:
            flash("Already friends!")
            return redirect("/friends")
            
        # Load confirmation page    
        names = db.execute("SELECT * FROM userinfo WHERE id = ?", user_id[0]['id'])
        return render_template("friendsfound.html", names=names[0], search=search)
        

@app.route("/friendsfound", methods=["GET", "POST"])
@login_required
def friendsfound():
    # Load confirmation page
    if request.method == "GET":
        return render_template("friendsfound.html")
    else:
        # Update table with new friend
        user_id = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("username"))
        db.execute("INSERT INTO friends (user_id, friend_id) VALUES (?, ?)", session["user_id"], user_id[0]["id"])
        flash("Friend added!")
        return redirect("/friends")
        

# Display user's own running statistics
@app.route("/friendprofile", methods=["GET", "POST"])
@login_required
def friendprofile():
    # Obtain running log
    runs = db.execute("SELECT * FROM runs WHERE user_id = ? ORDER BY year DESC, month DESC, day DESC", request.form.get("friend_id"))
    # Obtain personal info
    profile_info = db.execute("SELECT * FROM userinfo WHERE id = ?", request.form.get("friend_id"))
    return render_template("friendprofile.html", runs=runs, profile_info=profile_info[0])
    

@app.route("/removefriend", methods=["GET", "POST"])
@login_required
def removefriend():
    # Load confirmation page
    # Remove friend from table
    #user_id = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("username"))
    db.execute("DELETE FROM friends WHERE friend_id=? AND user_id=?", request.form.get("id"), session["user_id"])
    flash("Friend removed")
    return redirect("/friends")

def errorhandler(e):
    """Handle error (adapted from finance)"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors (adapted from finance)
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
