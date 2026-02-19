from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from bson.objectid import ObjectId
import os

app = Flask(__name__)
app.secret_key = "secretkey"

# ---------------- MONGODB CONFIG ----------------
app.config["MONGO_URI"] = "mongodb+srv://zahidmomin019_db_user:Zahidmomin019@cluster10.ymo2mha.mongodb.net/jobportal?retryWrites=true&w=majority"
mongo = PyMongo(app)

# ---------------- EMAIL CONFIG ----------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'zahidmomin019@gmail.com'   # CHANGE
app.config['MAIL_PASSWORD'] = 'Zahidmomin@30'      # CHANGE

mail = Mail(app)

# ---------------- LOGIN CONFIG ----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ---------------- FILE UPLOAD CONFIG ----------------
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------------- USER CLASS ----------------
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.username = user_data["username"]
        self.email = user_data["email"]
        self.role = user_data["role"]

@login_manager.user_loader
def load_user(user_id):
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user:
        return User(user)
    return None

# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect(url_for("login"))

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        existing_user = mongo.db.users.find_one({"email": request.form["email"]})
        if existing_user:
            flash("Email already exists!")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(request.form["password"])

        mongo.db.users.insert_one({
            "username": request.form["username"],
            "email": request.form["email"],
            "password": hashed_password,
            "role": request.form["role"]
        })

        flash("Registered Successfully!")
        return redirect(url_for("login"))

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        user = mongo.db.users.find_one({"email": request.form["email"]})

        if user and check_password_hash(user["password"], request.form["password"]):
            login_user(User(user))

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user["role"] == "employer":
                return redirect(url_for("employer_dashboard"))
            else:
                return redirect(url_for("dashboard"))

        flash("Invalid Credentials")

    return render_template("login.html")

# ---------------- USER DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    jobs = mongo.db.jobs.find({"status": "approved"})
    my_applications = mongo.db.applications.find({"applicant_id": current_user.id})
    return render_template("dashboard.html", jobs=jobs, my_applications=my_applications)

# ---------------- EMPLOYER DASHBOARD ----------------
@app.route("/employer")
@login_required
def employer_dashboard():
    if current_user.role != "employer":
        return "Access Denied"

    jobs = mongo.db.jobs.find({"posted_by": current_user.id})
    return render_template("employer_dashboard.html", jobs=jobs)

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        return "Access Denied"

    jobs = mongo.db.jobs.find()
    return render_template("admin_dashboard.html", jobs=jobs)

# ---------------- APPROVE JOB ----------------
@app.route("/approve_job/<job_id>")
@login_required
def approve_job(job_id):

    if current_user.role != "admin":
        return "Access Denied"

    mongo.db.jobs.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": {"status": "approved"}}
    )

    flash("Job Approved!")
    return redirect(url_for("admin_dashboard"))

# ---------------- REJECT JOB ----------------
@app.route("/reject_job/<job_id>")
@login_required
def reject_job(job_id):

    if current_user.role != "admin":
        return "Access Denied"

    mongo.db.jobs.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": {"status": "rejected"}}
    )

    flash("Job Rejected!")
    return redirect(url_for("admin_dashboard"))

# ---------------- DELETE JOB ----------------
@app.route("/delete_job/<job_id>")
@login_required
def delete_job(job_id):

    if current_user.role != "admin":
        return "Access Denied"

    mongo.db.jobs.delete_one({"_id": ObjectId(job_id)})

    flash("Job Deleted!")
    return redirect(url_for("admin_dashboard"))

# ---------------- POST JOB ----------------
@app.route("/post_job", methods=["GET", "POST"])
@login_required
def post_job():

    if current_user.role not in ["admin", "employer"]:
        return "Access Denied"

    if request.method == "POST":

        mongo.db.jobs.insert_one({
            "title": request.form["title"],
            "company": request.form["company"],
            "location": request.form["location"],
            "description": request.form["description"],
            "posted_by": current_user.id,
            "status": "pending"
        })

        flash("Job submitted for approval!")

        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("employer_dashboard"))

    return render_template("post_job.html")

# ---------------- APPLY JOB ----------------
@app.route('/apply/<job_id>', methods=['GET', 'POST'])
@login_required
def apply(job_id):

    job = mongo.db.jobs.find_one({"_id": ObjectId(job_id)})

    if not job:
        return "Job Not Found"

    if request.method == 'POST':

        resume = request.files['resume']
        filename = secure_filename(resume.filename)
        resume.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        mongo.db.applications.insert_one({
            "job_id": job_id,
            "job_title": job["title"],
            "applicant_id": current_user.id,
            "applicant_name": current_user.username,
            "resume_filename": filename,
            "employer_id": job["posted_by"],
            "status": "Applied"
        })

        flash("Application Submitted!")
        return redirect(url_for("dashboard"))

    return render_template('apply_job.html', job=job)

# ---------------- VIEW APPLICATIONS ----------------
@app.route("/view_applications")
@login_required
def view_applications():

    if current_user.role not in ["admin", "employer"]:
        return "Access Denied"

    if current_user.role == "employer":
        applications = mongo.db.applications.find({"employer_id": current_user.id})
    else:
        applications = mongo.db.applications.find()

    return render_template("view_applications.html", applications=applications)

# ---------------- SCHEDULE INTERVIEW ----------------
@app.route("/schedule_interview/<application_id>", methods=["GET", "POST"])
@login_required
def schedule_interview(application_id):

    application = mongo.db.applications.find_one({"_id": ObjectId(application_id)})

    if not application:
        return "Application Not Found"

    if request.method == "POST":

        mongo.db.applications.update_one(
            {"_id": ObjectId(application_id)},
            {"$set": {
                "interview_date": request.form["interview_date"],
                "status": "Interview Scheduled"
            }}
        )

        flash("Interview Scheduled!")
        return redirect(url_for("view_applications"))

    return render_template("schedule_interview.html", application=application)

# ---------------- REJECT CANDIDATE ----------------
@app.route("/reject_candidate/<application_id>")
@login_required
def reject_candidate(application_id):

    application = mongo.db.applications.find_one({"_id": ObjectId(application_id)})

    mongo.db.applications.update_one(
        {"_id": ObjectId(application_id)},
        {"$set": {"status": "Rejected"}}
    )

    user = mongo.db.users.find_one({"_id": ObjectId(application["applicant_id"])})

    msg = Message(
        subject="Application Rejected",
        sender=app.config['MAIL_USERNAME'],
        recipients=[user["email"]]
    )
    msg.body = f"Hello {user['username']},\n\nYour application for {application['job_title']} has been rejected."

    mail.send(msg)

    flash("Candidate Rejected & Email Sent!")
    return redirect(url_for("view_applications"))

# ---------------- SELECT CANDIDATE ----------------
@app.route("/select_candidate/<application_id>")
@login_required
def select_candidate(application_id):

    application = mongo.db.applications.find_one({"_id": ObjectId(application_id)})

    mongo.db.applications.update_one(
        {"_id": ObjectId(application_id)},
        {"$set": {"status": "Selected"}}
    )

    user = mongo.db.users.find_one({"_id": ObjectId(application["applicant_id"])})

    msg = Message(
        subject="Congratulations! Selected",
        sender=app.config['MAIL_USERNAME'],
        recipients=[user["email"]]
    )
    msg.body = f"Hello {user['username']},\n\nCongratulations! You are selected for {application['job_title']}."

    mail.send(msg)

    flash("Candidate Selected & Email Sent!")
    return redirect(url_for("view_applications"))

# ---------------- DOWNLOAD RESUME ----------------
@app.route('/uploads/<filename>')
@login_required
def download_resume(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
