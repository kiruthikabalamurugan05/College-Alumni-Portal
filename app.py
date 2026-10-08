from flask import Flask, render_template, request, redirect, url_for, flash, session

from werkzeug.security import generate_password_hash, check_password_hash

from pymongo import MongoClient

from bson.objectid import ObjectId

from pymongo.errors import DuplicateKeyError

from datetime import datetime



app = Flask(__name__)

app.secret_key = "college_alumni_portal_secret_key"



# =========================================================

# MONGODB

# =========================================================



client = MongoClient("mongodb://localhost:27017/")

db = client["college_alumni_portal"]



colleges_collection = db["colleges"]

students_collection = db["students"]

alumni_collection = db["alumni"]

users_collection = db["users"]



activity_collection = db["activity_logs"]





def log_activity(action, description, user_name="", role=""):

    activity_collection.insert_one({

        "action": action,

        "description": description,

        "user_name": user_name,

        "role": role,

        "created_at": datetime.now()

    })



def current_user_name():
    user = users_collection.find_one({"email": session.get("email")})
    if user:
        return user.get("full_name") or user.get("email", "User")
    return session.get("email", "User")


def require_platform_admin():
    return session.get("role") == "platform_admin"


# Prevent duplicate emails and college codes

users_collection.create_index("email", unique=True)

colleges_collection.create_index("college_code", unique=True)



# =========================================================

# PLATFORM ADMIN

# =========================================================



ADMIN_EMAIL = "alumniportal@gmail.com"

ADMIN_PASSWORD = "AlumniPortalAdmin@123"



if not users_collection.find_one({"email": ADMIN_EMAIL}):

    users_collection.insert_one({

        "email": ADMIN_EMAIL,

        "password": generate_password_hash(ADMIN_PASSWORD),

        "role": "platform_admin",

        "status": "Active"

    })





# =========================================================

# HOME

# =========================================================



@app.route("/")

def home():

    return render_template("index.html")





# =========================================================

# LOGIN

# =========================================================



@app.route("/login", methods=["GET", "POST"])

def login():



    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()

        password = request.form.get("password", "")



        user = users_collection.find_one({"email": email})



        if user and check_password_hash(user["password"], password):

            if user.get("status") in ["Pending", "Rejected", "Inactive"]:
                flash(
                    f"Your account is currently {user.get('status', 'inactive').lower()}. Please contact the administrator.",
                    "error"
                )
                return render_template("login.html")

            session["email"] = user["email"]
            session["role"] = user["role"]
            if user.get("college_id"):
                session["college_id"] = str(user.get("college_id"))
            else:
                session.pop("college_id", None)

            log_activity(
                "User logged in",
                f"{user.get('full_name', user.get('email', 'User'))} logged in ({user.get('role', 'user')}).",
                user.get("full_name", user.get("email", "User")),
                user.get("role", "")
            )

            if user["role"] == "platform_admin":

                return redirect(url_for("admin_dashboard"))

            elif user["role"] == "college_admin":

                return redirect(url_for("college_admin_dashboard"))

            elif user["role"] == "student":

                return redirect(url_for("student_dashboard"))

            elif user["role"] == "alumni":

                return redirect(url_for("alumni_dashboard"))



        flash("Invalid email or password.", "error")



    return render_template("login.html")





# =========================================================

# COLLEGE REGISTRATION

# =========================================================



@app.route("/register-college", methods=["GET", "POST"])

def register_college():



    if request.method == "POST":



        college_name = request.form.get("college_name", "").strip()

        college_code = request.form.get("college_code", "").strip()

        university = request.form.get("university", "").strip()

        established_year = request.form.get("established_year", "").strip()

        college_email = request.form.get("college_email", "").strip().lower()

        college_phone = request.form.get("college_phone", "").strip()

        campus_address = request.form.get("campus_address", "").strip()

        city = request.form.get("city", "").strip()

        state = request.form.get("state", "").strip()

        pincode = request.form.get("pincode", "").strip()

        website = request.form.get("website", "").strip()

        college_description = request.form.get("college_description", "").strip()



        admin_name = request.form.get("admin_name", "").strip()

        admin_email = request.form.get("admin_email", "").strip().lower()

        admin_phone = request.form.get("admin_phone", "").strip()

        admin_password = request.form.get("admin_password", "")



        if not college_name or not college_code:

            flash("College name and college code are required.", "error")

            return redirect(url_for("register_college"))



        if not college_email or not admin_email or not admin_password:

            flash("College email, admin email and admin password are required.", "error")

            return redirect(url_for("register_college"))



        if colleges_collection.find_one({

            "college_code": {"$regex": f"^{college_code}$", "$options": "i"}

        }):

            flash("College code already exists.", "error")

            return redirect(url_for("register_college"))



        if users_collection.find_one({"email": admin_email}):

            flash("Admin email already exists.", "error")

            return redirect(url_for("register_college"))



        college = {

            "college_name": college_name,

            "college_code": college_code,

            "university": university,

            "established_year": established_year,

            "college_email": college_email,

            "college_phone": college_phone,

            "campus_address": campus_address,

            "city": city,

            "state": state,

            "pincode": pincode,

            "website": website,

            "college_description": college_description,

            "admin_name": admin_name,

            "admin_email": admin_email,

            "admin_phone": admin_phone,

            "admin_password": generate_password_hash(admin_password),

            "status": "Pending"

        }



        try:

            colleges_collection.insert_one(college)

        except DuplicateKeyError:

            flash("College code already exists.", "error")

            return redirect(url_for("register_college"))



        flash(

            "College registration submitted successfully. Waiting for Platform Admin approval.",

            "success"

        )

        return redirect(url_for("register_college"))



    return render_template("register_college.html")





# =========================================================

# STUDENT REGISTRATION

# =========================================================



@app.route("/register-student", methods=["GET", "POST"])

def register_student():



    approved_colleges = list(

        colleges_collection.find({"status": "Approved"}).sort("college_name", 1)

    )



    if request.method == "POST":



        college_id = request.form.get("college_id", "")

        full_name = request.form.get("full_name", "").strip()

        email = request.form.get("email", "").strip().lower()

        password = request.form.get("password", "")

        confirm_password = request.form.get("confirm_password", "")

        phone = request.form.get("phone", "").strip()

        gender = request.form.get("gender", "")

        date_of_birth = request.form.get("date_of_birth", "")

        register_number = request.form.get("register_number", "").strip()

        degree = request.form.get("degree", "").strip()

        department = request.form.get("department", "").strip()

        batch = request.form.get("batch", "").strip()

        graduation_year = request.form.get("graduation_year", "")



        if password != confirm_password:

            flash("Passwords do not match.", "error")

            return redirect(url_for("register_student"))



        if users_collection.find_one({"email": email}):

            flash("Email already registered.", "error")

            return redirect(url_for("register_student"))



        selected_college = None

        if ObjectId.is_valid(college_id):

            selected_college = colleges_collection.find_one({

                "_id": ObjectId(college_id),

                "status": "Approved"

            })



        if not selected_college:

            flash("Please select a valid approved college.", "error")

            return redirect(url_for("register_student"))



        hashed_password = generate_password_hash(password)



        student = {

            "college_id": selected_college["_id"],

            "college_name": selected_college["college_name"],

            "college_code": selected_college["college_code"],

            "full_name": full_name,

            "email": email,

            "password": hashed_password,

            "phone": phone,

            "gender": gender,

            "date_of_birth": date_of_birth,

            "register_number": register_number,

            "degree": degree,

            "department": department,

            "batch": batch,

            "graduation_year": graduation_year,

            "status": "Pending"

        }



        try:

            students_collection.insert_one(student)

            users_collection.insert_one({

                "email": email,

                "password": hashed_password,

                "role": "student",

                "college_id": selected_college["_id"],

                "college_name": selected_college["college_name"],

                "college_code": selected_college["college_code"],

                "full_name": full_name,

                "status": "Pending"

            })

            log_activity(
                "Student registered",
                f"{full_name} registered and is waiting for College Admin approval.",
                full_name,
                "student"
            )

        except DuplicateKeyError:

            flash("Email already registered.", "error")

            return redirect(url_for("register_student"))



        flash(

            "Student registration submitted successfully. Waiting for College Admin approval.",

            "success"

        )

        return redirect(url_for("register_student"))



    return render_template(

        "register_student.html",

        colleges=approved_colleges

    )





# =========================================================

# ALUMNI REGISTRATION

# =========================================================



@app.route("/register-alumni", methods=["GET", "POST"])

def register_alumni():



    approved_colleges = list(

        colleges_collection.find({"status": "Approved"}).sort("college_name", 1)

    )



    if request.method == "POST":



        college_id = request.form.get("college_id", "")

        full_name = request.form.get("full_name", "").strip()

        email = request.form.get("email", "").strip().lower()

        password = request.form.get("password", "")

        confirm_password = request.form.get("confirm_password", "")

        phone = request.form.get("phone", "").strip()

        gender = request.form.get("gender", "")

        current_location = request.form.get("current_location", "").strip()

        register_number = request.form.get("register_number", "").strip()

        degree = request.form.get("degree", "").strip()

        department = request.form.get("department", "").strip()

        batch = request.form.get("batch", "").strip()

        graduation_year = request.form.get("graduation_year", "")

        company = request.form.get("company", "").strip()

        job_title = request.form.get("job_title", "").strip()

        industry = request.form.get("industry", "").strip()

        experience = request.form.get("experience", "")

        skills = request.form.get("skills", "").strip()

        linkedin = request.form.get("linkedin", "").strip()

        github = request.form.get("github", "").strip()

        portfolio = request.form.get("portfolio", "").strip()

        mentorship = request.form.get("mentorship", "no")

        mentor_areas = request.form.getlist("mentor_areas")



        if password != confirm_password:

            flash("Passwords do not match.", "error")

            return redirect(url_for("register_alumni"))



        if users_collection.find_one({"email": email}):

            flash("Email already registered.", "error")

            return redirect(url_for("register_alumni"))



        selected_college = None

        if ObjectId.is_valid(college_id):

            selected_college = colleges_collection.find_one({

                "_id": ObjectId(college_id),

                "status": "Approved"

            })



        if not selected_college:

            flash("Please select a valid approved college.", "error")

            return redirect(url_for("register_alumni"))



        hashed_password = generate_password_hash(password)



        alumni_user = {

            "college_id": selected_college["_id"],

            "college_name": selected_college["college_name"],

            "college_code": selected_college["college_code"],

            "full_name": full_name,

            "email": email,

            "password": hashed_password,

            "phone": phone,

            "gender": gender,

            "current_location": current_location,

            "register_number": register_number,

            "degree": degree,

            "department": department,

            "batch": batch,

            "graduation_year": graduation_year,

            "company": company,

            "job_title": job_title,

            "industry": industry,

            "experience": experience,

            "skills": skills,

            "linkedin": linkedin,

            "github": github,

            "portfolio": portfolio,

            "mentorship": mentorship,

            "mentor_areas": mentor_areas,

            "status": "Pending"

        }



        try:

            alumni_collection.insert_one(alumni_user)

            users_collection.insert_one({

                "email": email,

                "password": hashed_password,

                "role": "alumni",

                "college_id": selected_college["_id"],

                "college_name": selected_college["college_name"],

                "college_code": selected_college["college_code"],

                "full_name": full_name,

                "status": "Pending"

            })

            log_activity(
                "Alumni registered",
                f"{full_name} registered and is waiting for College Admin approval.",
                full_name,
                "alumni"
            )

        except DuplicateKeyError:

            flash("Email already registered.", "error")

            return redirect(url_for("register_alumni"))



        flash(

            "Alumni registration submitted successfully. Waiting for College Admin approval.",

            "success"

        )

        return redirect(url_for("register_alumni"))



    return render_template(

        "register_alumni.html",

        colleges=approved_colleges

    )





# =========================================================

# PLATFORM ADMIN DASHBOARD

# =========================================================



@app.route("/admin/dashboard")

def admin_dashboard():



    if session.get("role") != "platform_admin":

        return redirect(url_for("login"))



    # =====================================================

    # COLLEGE STATISTICS

    # =====================================================



    total_colleges = colleges_collection.count_documents({})



    pending_colleges = colleges_collection.count_documents({

        "status": "Pending"

    })



    approved_colleges = colleges_collection.count_documents({

        "status": "Approved"

    })





    # =====================================================

    # USER STATISTICS

    # =====================================================



    total_students = students_collection.count_documents({})



    total_alumni = alumni_collection.count_documents({})



    total_users = users_collection.count_documents({})



    active_users = users_collection.count_documents({

        "status": {

            "$in": [

                "Approved",

                "Active"

            ]

        }

    })





    # =====================================================

    # CONNECTION STATISTICS

    # =====================================================



    connections_collection = db["connections"]



    total_connections = connections_collection.count_documents({

        "status": "Accepted"

    })





    # =====================================================

    # MESSAGE STATISTICS

    # =====================================================



    messages_collection = db["messages"]



    total_messages = messages_collection.count_documents({})





    # =====================================================

    # PENDING COLLEGES

    # =====================================================



    pending_college_list = list(

        colleges_collection.find({

            "status": "Pending"

        }).sort("_id", -1).limit(10)

    )





    # =====================================================

    # RECENT ACTIVITY

    # =====================================================



    recent_activities = list(

        activity_collection.find({})

        .sort("created_at", -1)

        .limit(10)

    )





    # =====================================================

    # RECENT COLLEGES

    # =====================================================



    recent_colleges = list(

        colleges_collection.find({})

        .sort("_id", -1)

        .limit(10)

    )





    return render_template(

        "admin_dashboard.html",



        total_colleges=total_colleges,



        pending_colleges=pending_colleges,



        approved_colleges=approved_colleges,



        total_students=total_students,



        total_alumni=total_alumni,



        total_users=total_users,



        active_users=active_users,



        total_connections=total_connections,



        total_messages=total_messages,



        pending_college_list=pending_college_list,



        recent_activities=recent_activities,



        recent_colleges=recent_colleges

    )

# =========================================================

# FIND COLLEGE

# =========================================================



def get_college(college_id):



    if ObjectId.is_valid(str(college_id)):

        return colleges_collection.find_one({

            "_id": ObjectId(str(college_id))

        })



    # Compatibility with an older template that sends loop.index0

    try:

        index = int(college_id)

        colleges = list(colleges_collection.find().sort("_id", -1))

        if 0 <= index < len(colleges):

            return colleges[index]

    except (ValueError, TypeError):

        pass



    return None





# =========================================================

# APPROVE COLLEGE

# =========================================================



@app.route("/approve-college/<college_id>")

def approve_college(college_id):



    if session.get("role") != "platform_admin":

        return redirect(url_for("login"))



    college = get_college(college_id)



    if not college:

        flash("College not found.", "error")

        return redirect(url_for("admin_dashboard"))



    colleges_collection.update_one(

        {"_id": college["_id"]},

        {"$set": {"status": "Approved"}}

    )



    # Create college admin login after approval

    if not users_collection.find_one({

        "email": college["admin_email"]

    }):

        users_collection.insert_one({

            "email": college["admin_email"],

            "password": college["admin_password"],

            "role": "college_admin",

            "college_id": college["_id"],

            "college_name": college["college_name"],

            "college_code": college["college_code"],

            "full_name": college.get("admin_name", ""),

            "status": "Active"

        })



    log_activity(
        "College approved",
        f"{college.get('college_name', 'College')} was approved by Platform Admin.",
        current_user_name(), "platform_admin"
    )

    flash("College approved successfully.", "success")

    return redirect(url_for("admin_dashboard"))





# =========================================================

# REJECT COLLEGE

# =========================================================



@app.route("/reject-college/<college_id>")

def reject_college(college_id):



    if session.get("role") != "platform_admin":

        return redirect(url_for("login"))



    college = get_college(college_id)



    if not college:

        flash("College not found.", "error")

        return redirect(url_for("admin_dashboard"))



    colleges_collection.update_one(

        {"_id": college["_id"]},

        {"$set": {"status": "Rejected"}}

    )



    log_activity(
        "College rejected",
        f"{college.get('college_name', 'College')} was rejected by Platform Admin.",
        current_user_name(), "platform_admin"
    )

    flash("College registration rejected.", "success")

    return redirect(url_for("admin_dashboard"))



# =========================================================

# =========================================================
# PLATFORM ADMIN - COLLEGE MANAGEMENT
# =========================================================


@app.route("/admin/colleges")
def admin_colleges():
    if not require_platform_admin():
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    query = {}

    if search:
        query["$or"] = [
            {"college_name": {"$regex": search, "$options": "i"}},
            {"college_code": {"$regex": search, "$options": "i"}},
            {"city": {"$regex": search, "$options": "i"}},
            {"state": {"$regex": search, "$options": "i"}}
        ]

    if status in ["Pending", "Approved", "Rejected"]:
        query["status"] = status

    colleges = list(colleges_collection.find(query).sort("_id", -1))

    return render_template("admin_colleges.html", colleges=colleges, search=search, status=status)


@app.route("/admin/college/<college_id>")
def admin_college_details(college_id):
    if not require_platform_admin():
        return redirect(url_for("login"))

    if not ObjectId.is_valid(college_id):
        flash("Invalid college.", "error")
        return redirect(url_for("admin_colleges"))

    college = colleges_collection.find_one({"_id": ObjectId(college_id)})
    if not college:
        flash("College not found.", "error")
        return redirect(url_for("admin_colleges"))

    students_count = students_collection.count_documents({"college_id": college["_id"]})
    alumni_count = alumni_collection.count_documents({"college_id": college["_id"]})
    users_count = users_collection.count_documents({"college_id": college["_id"]})
    connections_count = db["connections"].count_documents({"college_id": college["_id"]})

    return render_template(
        "admin_college_details.html",
        college=college,
        students_count=students_count,
        alumni_count=alumni_count,
        users_count=users_count,
        connections_count=connections_count
    )


# =========================================================
# PLATFORM ADMIN - USER MANAGEMENT
# =========================================================


@app.route("/admin/users")
def admin_users():
    if not require_platform_admin():
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    role = request.args.get("role", "").strip()
    status = request.args.get("status", "").strip()
    query = {}

    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"college_name": {"$regex": search, "$options": "i"}}
        ]

    if role in ["student", "alumni", "college_admin", "platform_admin"]:
        query["role"] = role
    if status in ["Active", "Inactive", "Pending", "Rejected"]:
        query["status"] = status

    users = list(users_collection.find(query).sort("_id", -1))

    return render_template(
        "admin_users.html", users=users, search=search,
        selected_role=role, selected_status=status
    )


@app.route("/admin/users/toggle/<user_id>")
def toggle_user_status(user_id):
    if not require_platform_admin():
        return redirect(url_for("login"))

    if not ObjectId.is_valid(user_id):
        flash("Invalid user.", "error")
        return redirect(url_for("admin_users"))

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin_users"))

    if user.get("role") == "platform_admin":
        flash("Platform Admin cannot be deactivated.", "error")
        return redirect(url_for("admin_users"))

    current_status = user.get("status", "Active")
    new_status = "Inactive" if current_status == "Active" else "Active"

    users_collection.update_one({"_id": user["_id"]}, {"$set": {"status": new_status}})

    if user.get("role") == "student":
        students_collection.update_one(
            {"email": user.get("email")},
            {"$set": {"status": "Approved" if new_status == "Active" else "Inactive"}}
        )
    elif user.get("role") == "alumni":
        alumni_collection.update_one(
            {"email": user.get("email")},
            {"$set": {"status": "Approved" if new_status == "Active" else "Inactive"}}
        )

    log_activity(
        f"User {new_status.lower()}",
        f"{user.get('full_name', user.get('email', 'User'))} was marked {new_status}.",
        current_user_name(), "platform_admin"
    )

    flash(f"User status changed to {new_status}.", "success")
    return redirect(url_for("admin_users"))


# =========================================================
# PLATFORM ADMIN - BROADCAST ANNOUNCEMENTS
# =========================================================

@app.route("/admin/broadcast", methods=["GET", "POST"])
def admin_broadcast():

    if not require_platform_admin():
        return redirect(url_for("login"))

    announcements_collection = db["announcements"]

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()
        target = request.form.get("target", "all").strip()
        college_id = request.form.get("college_id", "").strip()

        if not title or not message:
            flash("Title and message are required.", "error")
            return redirect(url_for("admin_broadcast"))

        announcement = {
            "title": title,
            "message": message,
            "target": target,
            "created_by": session.get("email"),
            "created_at": datetime.now(),
            "college_id": None
        }

        if target == "college":

            if not ObjectId.is_valid(college_id):
                flash("Please select a valid college.", "error")
                return redirect(url_for("admin_broadcast"))

            selected_college = colleges_collection.find_one({
                "_id": ObjectId(college_id),
                "status": "Approved"
            })

            if not selected_college:
                flash("Selected college is not valid or approved.", "error")
                return redirect(url_for("admin_broadcast"))

            announcement["college_id"] = selected_college["_id"]

        announcements_collection.insert_one(announcement)

        flash(
            "Announcement published successfully.",
            "success"
        )

        return redirect(url_for("admin_broadcast"))

    colleges = list(
        colleges_collection.find(
            {"status": "Approved"}
        ).sort("college_name", 1)
    )

    return render_template(
        "admin_broadcast.html",
        colleges=colleges
    )


# =========================================================
# PLATFORM ADMIN - AUDIT LOGS
# =========================================================


@app.route("/admin/audit-logs")
def admin_audit_logs():
    if not require_platform_admin():
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    role = request.args.get("role", "").strip()
    query = {}

    if search:
        query["$or"] = [
            {"action": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"user_name": {"$regex": search, "$options": "i"}}
        ]
    if role:
        query["role"] = role

    logs = list(activity_collection.find(query).sort("created_at", -1).limit(200))
    return render_template(
        "admin_audit_logs.html", logs=logs, search=search, selected_role=role
    )


# COLLEGE ADMIN DASHBOARD

# =========================================================



# ============================================================
# COLLEGE ADMIN DASHBOARD
# ============================================================

@app.route("/college-admin/dashboard")
def college_admin_dashboard():

    # ---------------------------------------------------------
    # CHECK LOGIN
    # ---------------------------------------------------------

    if session.get("role") != "college_admin":
        return redirect(url_for("login"))

    # ---------------------------------------------------------
    # GET LOGGED-IN COLLEGE ADMIN
    # ---------------------------------------------------------

    admin_email = session.get("email")

    college_admin = users_collection.find_one({
        "email": admin_email,
        "role": "college_admin"
    })

    if not college_admin:
        flash("College admin account not found.", "error")
        return redirect(url_for("logout"))

    # ---------------------------------------------------------
    # GET COLLEGE ID
    # ---------------------------------------------------------

    college_id = college_admin.get("college_id")

    if not college_id:
        flash("College information not linked to this admin.", "error")
        return redirect(url_for("logout"))

    # ---------------------------------------------------------
    # GET COLLEGE
    # ---------------------------------------------------------

    college = colleges_collection.find_one({
        "_id": college_id
    })

    if not college:
        flash("College information not found.", "error")
        return redirect(url_for("logout"))

    # =========================================================
    # STUDENTS
    # =========================================================

    total_students = students_collection.count_documents({
        "college_id": college_id
    })

    # Pending students
    pending_student_list = list(
        students_collection.find({
            "college_id": college_id,
            "status": "Pending"
        }).sort("_id", -1)
    )

    pending_students = len(pending_student_list)

    # Approved students
    approved_students = students_collection.count_documents({
        "college_id": college_id,
        "status": "Approved"
    })

    # Rejected students
    rejected_students = students_collection.count_documents({
        "college_id": college_id,
        "status": "Rejected"
    })

    # =========================================================
    # ALUMNI
    # =========================================================

    total_alumni = alumni_collection.count_documents({
        "college_id": college_id
    })

    # Pending alumni
    pending_alumni_list = list(
        alumni_collection.find({
            "college_id": college_id,
            "status": "Pending"
        }).sort("_id", -1)
    )

    pending_alumni = len(pending_alumni_list)

    # Approved alumni
    approved_alumni = alumni_collection.count_documents({
        "college_id": college_id,
        "status": "Approved"
    })

    # Rejected alumni
    rejected_alumni = alumni_collection.count_documents({
        "college_id": college_id,
        "status": "Rejected"
    })

    # =========================================================
    # PENDING COUNT
    # =========================================================

    pending_count = pending_students + pending_alumni

    # =========================================================
    # ACTIVE USERS
    # =========================================================

    active_users = users_collection.count_documents({
        "college_id": college_id,
        "status": "Active"
    })

    # =========================================================
    # ALUMNI MENTORS
    # =========================================================

    alumni_mentors = alumni_collection.count_documents({
        "college_id": college_id,
        "mentorship": "yes",
        "status": "Approved"
    })

    # =========================================================
    # CONNECTIONS
    # =========================================================

    connections_collection = db["connections"]

    connections = connections_collection.count_documents({
        "college_id": college_id
    })

    # =========================================================
    # ANNOUNCEMENTS
    # =========================================================

    announcements_collection = db["announcements"]

    announcements = list(
        announcements_collection.find({
            "college_id": college_id
        }).sort("_id", -1).limit(5)
    )

    # =========================================================
    # RECENT STUDENTS
    # =========================================================

    recent_students = list(
        students_collection.find({
            "college_id": college_id
        }).sort("_id", -1).limit(5)
    )

    # =========================================================
    # RECENT ALUMNI
    # =========================================================

    recent_alumni = list(
        alumni_collection.find({
            "college_id": college_id
        }).sort("_id", -1).limit(5)
    )

    # =========================================================
    # RENDER EXISTING DASHBOARD
    # =========================================================

    return render_template(
        "college_dashboard.html",

        # Admin information
        college_admin=college_admin,

        # College information
        college=college,

        # Student information
        total_students=total_students,
        pending_students=pending_students,
        approved_students=approved_students,
        rejected_students=rejected_students,
        pending_student_list=pending_student_list,
        recent_students=recent_students,

        # Alumni information
        total_alumni=total_alumni,
        pending_alumni=pending_alumni,
        approved_alumni=approved_alumni,
        rejected_alumni=rejected_alumni,
        pending_alumni_list=pending_alumni_list,
        recent_alumni=recent_alumni,

        # Other dashboard information
        pending_count=pending_count,
        active_users=active_users,
        alumni_mentors=alumni_mentors,
        connections=connections,
        announcements=announcements
    )
# =========================================================
# COLLEGE ADMIN - ALUMNI MANAGEMENT
# =========================================================

@app.route("/college-admin/alumni")
def college_admin_alumni():

    if session.get("role") != "college_admin":
        return redirect(url_for("login"))

    # Get logged-in college admin
    college_admin = users_collection.find_one({
        "email": session.get("email"),
        "role": "college_admin"
    })

    if not college_admin:
        flash("College admin account not found.", "error")
        return redirect(url_for("logout"))

    college_id = college_admin.get("college_id")

    # Get college
    college = colleges_collection.find_one({
        "_id": college_id
    })

    if not college:
        flash("College information not found.", "error")
        return redirect(url_for("logout"))

    # Search
    search = request.args.get("search", "").strip()

    # Status filter
    status = request.args.get("status", "").strip()

    # Base query - only alumni from this college
    query = {
        "college_id": college_id
    }

    # Search by name, email, company or job title
    if search:
        query["$or"] = [
            {
                "full_name": {
                    "$regex": search,
                    "$options": "i"
                }
            },
            {
                "email": {
                    "$regex": search,
                    "$options": "i"
                }
            },
            {
                "company": {
                    "$regex": search,
                    "$options": "i"
                }
            },
            {
                "job_title": {
                    "$regex": search,
                    "$options": "i"
                }
            }
        ]

    # Status filter
    if status:
        query["status"] = status

    # Get alumni
    alumni = list(
        alumni_collection.find(query).sort("_id", -1)
    )

    return render_template(
        "college_alumni.html",
        college=college,
        college_admin=college_admin,
        alumni=alumni,
        search=search,
        selected_status=status
    )
# =========================================================
# COLLEGE ADMIN - ANNOUNCEMENTS
# =========================================================

@app.route("/college-admin/announcements", methods=["GET", "POST"])
def college_admin_announcements():

    if session.get("role") != "college_admin":
        return redirect(url_for("login"))

    # Get logged-in college admin
    college_admin = users_collection.find_one({
        "email": session.get("email"),
        "role": "college_admin"
    })

    if not college_admin:
        flash("College admin account not found.", "error")
        return redirect(url_for("logout"))

    college_id = college_admin.get("college_id")

    # Get college
    college = colleges_collection.find_one({
        "_id": college_id
    })

    if not college:
        flash("College information not found.", "error")
        return redirect(url_for("logout"))

    announcements_collection = db["announcements"]

    # =====================================================
    # POST - CREATE ANNOUNCEMENT
    # =====================================================

    if request.method == "POST":

        title = request.form.get("title", "").strip()

        message = request.form.get(
            "message",
            request.form.get("description", "")
        ).strip()

        target = request.form.get(
            "target",
            request.form.get("audience", "all")
        ).strip()

        if not title:
            flash("Announcement title is required.", "error")
            return redirect(url_for("college_admin_announcements"))

        if not message:
            flash("Announcement content is required.", "error")
            return redirect(url_for("college_admin_announcements"))

        announcement = {
            "title": title,
            "message": message,
            "description": message,
            "target": target,
            "college_id": college_id,
            "created_by": session.get("email"),
            "created_at": datetime.now()
        }

        announcements_collection.insert_one(announcement)

        log_activity(
            "College announcement created",
            f"College Admin published announcement: {title}",
            college_admin.get(
                "full_name",
                college_admin.get("email", "College Admin")
            ),
            "college_admin"
        )

        flash("Announcement published successfully.", "success")

        return redirect(
            url_for("college_admin_announcements")
        )

    # =====================================================
    # GET - DISPLAY COLLEGE ANNOUNCEMENTS
    # =====================================================

    announcements = list(
        announcements_collection.find({
            "college_id": college_id
        }).sort("_id", -1)
    )

    return render_template(
        "college_announcements.html",
        college=college,
        college_admin=college_admin,
        announcements=announcements
    )

# =========================================================

# APPROVE STUDENT

# =========================================================



@app.route("/college-admin/approve-student/<student_id>")

def approve_student(student_id):



    if session.get("role") != "college_admin":

        return redirect(url_for("login"))



    if not ObjectId.is_valid(student_id):

        flash("Invalid student.", "error")

        return redirect(url_for("college_admin_dashboard"))



    student = students_collection.find_one({

        "_id": ObjectId(student_id)

    })



    if not student:

        flash("Student not found.", "error")

        return redirect(url_for("college_admin_dashboard"))



    # Make sure this student belongs to this college

    admin = users_collection.find_one({

        "email": session.get("email"),

        "role": "college_admin"

    })



    if not admin or student.get("college_id") != admin.get("college_id"):

        flash("Unauthorized action.", "error")

        return redirect(url_for("college_admin_dashboard"))



    students_collection.update_one(

        {"_id": ObjectId(student_id)},

        {"$set": {"status": "Approved"}}

    )



    users_collection.update_one(

        {

            "email": student["email"],

            "role": "student"

        },

        {"$set": {"status": "Active"}}

    )



    flash("Student approved successfully.", "success")



    return redirect(url_for("college_admin_dashboard"))





# =========================================================

# REJECT STUDENT

# =========================================================



@app.route("/college-admin/reject-student/<student_id>")

def reject_student(student_id):



    if session.get("role") != "college_admin":

        return redirect(url_for("login"))



    if not ObjectId.is_valid(student_id):

        flash("Invalid student.", "error")

        return redirect(url_for("college_admin_dashboard"))



    student = students_collection.find_one({

        "_id": ObjectId(student_id)

    })



    if not student:

        flash("Student not found.", "error")

        return redirect(url_for("college_admin_dashboard"))



    admin = users_collection.find_one({

        "email": session.get("email"),

        "role": "college_admin"

    })



    if not admin or student.get("college_id") != admin.get("college_id"):

        flash("Unauthorized action.", "error")

        return redirect(url_for("college_admin_dashboard"))



    students_collection.update_one(

        {"_id": ObjectId(student_id)},

        {"$set": {"status": "Rejected"}}

    )



    users_collection.update_one(

        {

            "email": student["email"],

            "role": "student"

        },

        {"$set": {"status": "Rejected"}}

    )



    flash("Student registration rejected.", "success")



    return redirect(url_for("college_admin_dashboard"))



# =========================================================

# APPROVE ALUMNI

# =========================================================





# =========================================================

# REJECT ALUMNI

# =========================================================



@app.route("/college-admin/reject-alumni/<alumni_id>")
def college_admin_reject_alumni(alumni_id):

    if session.get("role") != "college_admin":
        return redirect(url_for("login"))

    # Validate alumni ID
    if not ObjectId.is_valid(str(alumni_id)):
        flash("Invalid alumni ID.", "error")
        return redirect(url_for("college_admin_dashboard"))

    alumni = alumni_collection.find_one({
        "_id": ObjectId(str(alumni_id))
    })

    if not alumni:
        flash("Alumni not found.", "error")
        return redirect(url_for("college_admin_dashboard"))

    # Find logged-in college admin
    admin = users_collection.find_one({
        "email": session.get("email"),
        "role": "college_admin"
    })

    if not admin:
        flash("College admin account not found.", "error")
        return redirect(url_for("login"))

    admin_college_id = admin.get("college_id")

    # If admin has no college_id, try recovering it
    if not admin_college_id:

        college = colleges_collection.find_one({
            "admin_email": session.get("email")
        })

        if college:
            admin_college_id = college["_id"]

            users_collection.update_one(
                {"_id": admin["_id"]},
                {
                    "$set": {
                        "college_id": admin_college_id,
                        "college_name": college.get("college_name"),
                        "college_code": college.get("college_code")
                    }
                }
            )
        else:
            flash("College Admin is not linked to a college.", "error")
            return redirect(url_for("college_admin_dashboard"))

    # Convert string college_id safely
    if isinstance(admin_college_id, str):

        if not ObjectId.is_valid(admin_college_id):
            flash("Invalid college ID.", "error")
            return redirect(url_for("college_admin_dashboard"))

        admin_college_id = ObjectId(admin_college_id)

    alumni_college_id = alumni.get("college_id")

    # Handle old alumni record without college_id
    if not alumni_college_id:

        alumni_collection.update_one(
            {"_id": alumni["_id"]},
            {
                "$set": {
                    "college_id": admin_college_id
                }
            }
        )

        alumni_college_id = admin_college_id

    # Verify same college
    if str(alumni_college_id) != str(admin_college_id):

        flash(
            "Unauthorized action. Alumni belongs to another college.",
            "error"
        )

        return redirect(url_for("college_admin_dashboard"))

    # Reject alumni
    alumni_collection.update_one(
        {"_id": alumni["_id"]},
        {
            "$set": {
                "status": "Rejected"
            }
        }
    )

    # Update alumni login status
    users_collection.update_one(
        {
            "email": alumni.get("email"),
            "role": "alumni"
        },
        {
            "$set": {
                "status": "Rejected",
                "college_id": admin_college_id
            }
        }
    )

    try:
        log_activity(
            "Alumni rejected",
            f"{alumni.get('full_name', 'Alumni')} was rejected.",
            alumni.get("full_name", "Alumni"),
            "college_admin"
        )
    except Exception:
        pass

    flash("Alumni registration rejected.", "success")

    return redirect(url_for("college_admin_dashboard"))

@app.route("/college-admin/suspend-student/<student_id>")
def college_admin_suspend_student(student_id):

    if session.get("role") != "college_admin":
        return redirect(url_for("login"))

    if not ObjectId.is_valid(str(student_id)):
        flash("Invalid student ID.", "error")
        return redirect(url_for("college_admin_students"))

    admin = users_collection.find_one({
        "email": session.get("email"),
        "role": "college_admin"
    })

    if not admin:
        flash("College admin account not found.", "error")
        return redirect(url_for("login"))

    student = students_collection.find_one({
        "_id": ObjectId(str(student_id))
    })

    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("college_admin_students"))

    if str(student.get("college_id")) != str(admin.get("college_id")):
        flash("Unauthorized action.", "error")
        return redirect(url_for("college_admin_students"))

    students_collection.update_one(
        {"_id": student["_id"]},
        {"$set": {"status": "Suspended"}}
    )

    users_collection.update_one(
        {
            "email": student.get("email"),
            "role": "student"
        },
        {"$set": {"status": "Suspended"}}
    )

    flash("Student suspended successfully.", "success")
    return redirect(url_for("college_admin_students"))


@app.route("/college-admin/activate-student/<student_id>")
def college_admin_activate_student(student_id):

    if session.get("role") != "college_admin":
        return redirect(url_for("login"))

    if not ObjectId.is_valid(str(student_id)):
        flash("Invalid student ID.", "error")
        return redirect(url_for("college_admin_students"))

    admin = users_collection.find_one({
        "email": session.get("email"),
        "role": "college_admin"
    })

    if not admin:
        flash("College admin account not found.", "error")
        return redirect(url_for("login"))

    student = students_collection.find_one({
        "_id": ObjectId(str(student_id))
    })

    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("college_admin_students"))

    if str(student.get("college_id")) != str(admin.get("college_id")):
        flash("Unauthorized action.", "error")
        return redirect(url_for("college_admin_students"))

    students_collection.update_one(
        {"_id": student["_id"]},
        {"$set": {"status": "Approved"}}
    )

    users_collection.update_one(
        {
            "email": student.get("email"),
            "role": "student"
        },
        {"$set": {"status": "Active"}}
    )

    flash("Student activated successfully.", "success")
    return redirect(url_for("college_admin_students"))


@app.route("/college-admin/delete-student/<student_id>")
def college_admin_delete_student(student_id):

    if session.get("role") != "college_admin":
        return redirect(url_for("login"))

    if not ObjectId.is_valid(str(student_id)):
        flash("Invalid student ID.", "error")
        return redirect(url_for("college_admin_students"))

    admin = users_collection.find_one({
        "email": session.get("email"),
        "role": "college_admin"
    })

    if not admin:
        flash("College admin account not found.", "error")
        return redirect(url_for("login"))

    student = students_collection.find_one({
        "_id": ObjectId(str(student_id))
    })

    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("college_admin_students"))

    if str(student.get("college_id")) != str(admin.get("college_id")):
        flash("Unauthorized action.", "error")
        return redirect(url_for("college_admin_students"))

    students_collection.delete_one({
        "_id": student["_id"]
    })

    users_collection.delete_one({
        "email": student.get("email"),
        "role": "student"
    })

    flash("Student deleted successfully.", "success")
    return redirect(url_for("college_admin_students"))

@app.route("/college-admin/suspend-alumni/<alumni_id>")
def college_admin_suspend_alumni(alumni_id):

    if session.get("role") != "college_admin":
        return redirect(url_for("login"))

    if not ObjectId.is_valid(str(alumni_id)):
        flash("Invalid alumni ID.", "error")
        return redirect(url_for("college_admin_alumni"))

    admin = users_collection.find_one({
        "email": session.get("email"),
        "role": "college_admin"
    })

    if not admin:
        flash("College admin account not found.", "error")
        return redirect(url_for("login"))

    alumni = alumni_collection.find_one({
        "_id": ObjectId(str(alumni_id))
    })

    if not alumni:
        flash("Alumni not found.", "error")
        return redirect(url_for("college_admin_alumni"))

    if str(alumni.get("college_id")) != str(admin.get("college_id")):
        flash("Unauthorized action.", "error")
        return redirect(url_for("college_admin_alumni"))

    alumni_collection.update_one(
        {"_id": alumni["_id"]},
        {"$set": {"status": "Suspended"}}
    )

    users_collection.update_one(
        {
            "email": alumni.get("email"),
            "role": "alumni"
        },
        {"$set": {"status": "Suspended"}}
    )

    flash("Alumni suspended successfully.", "success")
    return redirect(url_for("college_admin_alumni"))


@app.route("/college-admin/activate-alumni/<alumni_id>")
def college_admin_activate_alumni(alumni_id):

    if session.get("role") != "college_admin":
        return redirect(url_for("login"))

    if not ObjectId.is_valid(str(alumni_id)):
        flash("Invalid alumni ID.", "error")
        return redirect(url_for("college_admin_alumni"))

    admin = users_collection.find_one({
        "email": session.get("email"),
        "role": "college_admin"
    })

    if not admin:
        flash("College admin account not found.", "error")
        return redirect(url_for("login"))

    alumni = alumni_collection.find_one({
        "_id": ObjectId(str(alumni_id))
    })

    if not alumni:
        flash("Alumni not found.", "error")
        return redirect(url_for("college_admin_alumni"))

    if str(alumni.get("college_id")) != str(admin.get("college_id")):
        flash("Unauthorized action.", "error")
        return redirect(url_for("college_admin_alumni"))

    alumni_collection.update_one(
        {"_id": alumni["_id"]},
        {"$set": {"status": "Approved"}}
    )

    users_collection.update_one(
        {
            "email": alumni.get("email"),
            "role": "alumni"
        },
        {"$set": {"status": "Active"}}
    )

    flash("Alumni activated successfully.", "success")
    return redirect(url_for("college_admin_alumni"))


@app.route("/college-admin/delete-alumni/<alumni_id>")
def college_admin_delete_alumni(alumni_id):

    if session.get("role") != "college_admin":
        return redirect(url_for("login"))

    if not ObjectId.is_valid(str(alumni_id)):
        flash("Invalid alumni ID.", "error")
        return redirect(url_for("college_admin_alumni"))

    admin = users_collection.find_one({
        "email": session.get("email"),
        "role": "college_admin"
    })

    if not admin:
        flash("College admin account not found.", "error")
        return redirect(url_for("login"))

    alumni = alumni_collection.find_one({
        "_id": ObjectId(str(alumni_id))
    })

    if not alumni:
        flash("Alumni not found.", "error")
        return redirect(url_for("college_admin_alumni"))

    if str(alumni.get("college_id")) != str(admin.get("college_id")):
        flash("Unauthorized action.", "error")
        return redirect(url_for("college_admin_alumni"))

    alumni_collection.delete_one({
        "_id": alumni["_id"]
    })

    users_collection.delete_one({
        "email": alumni.get("email"),
        "role": "alumni"
    })

    flash("Alumni deleted successfully.", "success")
    return redirect(url_for("college_admin_alumni"))



@app.route("/student/dashboard")

def student_dashboard():



    if session.get("role") != "student":

        return redirect(url_for("login"))



    student = students_collection.find_one({

        "email": session.get("email")

    })



    if not student:

        flash("Student account not found.", "error")

        return redirect(url_for("logout"))



    college_id = student.get("college_id")



    college = colleges_collection.find_one({

        "_id": college_id

    })



    # Approved alumni from the same college

    alumni_suggestions = list(

        alumni_collection.find({

            "college_id": college_id,

            "status": "Approved"

        }).limit(6)

    )



    # College announcements

    announcements_collection = db["announcements"]



    announcements = list(

        announcements_collection.find({

            "college_id": college_id

        }).sort("_id", -1).limit(5)

    )



    # Mentorship tasks

    tasks_collection = db["tasks"]



    tasks = list(

        tasks_collection.find({

            "student_id": student["_id"]

        }).sort("_id", -1).limit(5)

    )



    # Simple profile completion calculation

    profile_fields = [

        "full_name",

        "email",

        "phone",

        "gender",

        "current_location",

        "register_number",

        "degree",

        "department",

        "batch"

    ]



    completed_fields = 0



    for field in profile_fields:

        if student.get(field):

            completed_fields += 1



    profile_completion = int(

        (completed_fields / len(profile_fields)) * 100

    )



    return render_template(

        "student_dashboard.html",

        student=student,

        college=college,

        alumni_suggestions=alumni_suggestions,

        announcements=announcements,

        tasks=tasks,

        profile_completion=profile_completion

    )



@app.route("/student/find-alumni")

def find_alumni():



    if session.get("role") != "student":

        return redirect(url_for("login"))



    student = students_collection.find_one({

        "email": session.get("email")

    })



    if not student:

        flash("Student account not found.", "error")

        return redirect(url_for("logout"))



    college_id = student.get("college_id")



    college = colleges_collection.find_one({

        "_id": college_id

    })



    # Search values

    search = request.args.get("search", "").strip()

    selected_department = request.args.get(

        "department", ""

    ).strip()



    # Only approved alumni from the same college

    query = {

        "college_id": college_id,

        "status": "Approved"

    }



    if search:

        query["$or"] = [

            {

                "full_name": {

                    "$regex": search,

                    "$options": "i"

                }

            },

            {

                "company": {

                    "$regex": search,

                    "$options": "i"

                }

            },

            {

                "job_title": {

                    "$regex": search,

                    "$options": "i"

                }

            }

        ]



    if selected_department:

        query["department"] = selected_department



    alumni = list(

        alumni_collection.find(query).sort(

            "full_name", 1

        )

    )



    # Get departments for filter

    departments = alumni_collection.distinct(

        "department",

        {

            "college_id": college_id,

            "status": "Approved"

        }

    )



    departments = [

        department

        for department in departments

        if department

    ]



    return render_template(

        "find_alumni.html",

        student=student,

        college=college,

        alumni=alumni,

        departments=departments,

        search=search,

        selected_department=selected_department

    )



@app.route("/student/alumni/<alumni_id>")

def alumni_profile(alumni_id):



    if session.get("role") != "student":

        return redirect(url_for("login"))





    student = students_collection.find_one({

        "email": session.get("email")

    })





    if not student:



        flash(

            "Student account not found.",

            "error"

        )



        return redirect(

            url_for("logout")

        )





    try:



        alumni_object_id = ObjectId(alumni_id)



    except Exception:



        flash(

            "Invalid alumni profile.",

            "error"

        )



        return redirect(

            url_for("find_alumni")

        )





    alumni = alumni_collection.find_one({



        "_id": alumni_object_id,



        "status": "Approved"



    })





    if not alumni:



        flash(

            "Alumni profile not found.",

            "error"

        )



        return redirect(

            url_for("find_alumni")

        )





    # Make sure the alumni belongs to

    # the same college



    if alumni.get("college_id") != student.get(

        "college_id"

    ):



        flash(

            "You cannot access this alumni profile.",

            "error"

        )



        return redirect(

            url_for("find_alumni")

        )





    college = colleges_collection.find_one({



        "_id": student.get("college_id")



    })





    # ================= CONNECTION =================



    connections_collection = db["connections"]



    connection = connections_collection.find_one({



        "student_id": student["_id"],



        "alumni_id": alumni["_id"]



    })





    connection_status = (



        connection.get("status")



        if connection



        else None



    )





    # ================= MENTORSHIP =================



    mentorship_collection = db[

        "mentorship_requests"

    ]





    mentorship = mentorship_collection.find_one({



        "student_id": student["_id"],



        "alumni_id": alumni["_id"]



    })





    mentorship_status = (



        mentorship.get("status")



        if mentorship



        else None



    )





    return render_template(



        "alumni_profile.html",



        student=student,



        alumni=alumni,



        college=college,



        connection_status=connection_status,



        mentorship_status=mentorship_status



    )

@app.route("/student/connect/<alumni_id>")

def connect_alumni(alumni_id):



    if session.get("role") != "student":

        return redirect(url_for("login"))



    student = students_collection.find_one({

        "email": session.get("email")

    })



    if not student:

        flash("Student account not found.", "error")

        return redirect(url_for("logout"))



    try:

        alumni_object_id = ObjectId(alumni_id)

    except Exception:

        flash("Invalid alumni.", "error")

        return redirect(url_for("find_alumni"))



    alumni = alumni_collection.find_one({

        "_id": alumni_object_id,

        "status": "Approved"

    })



    if not alumni:

        flash("Alumni not found.", "error")

        return redirect(url_for("find_alumni"))



    # Same college verification

    if alumni.get("college_id") != student.get("college_id"):

        flash("You cannot connect with this alumni.", "error")

        return redirect(url_for("find_alumni"))



    connections_collection = db["connections"]



    existing_connection = connections_collection.find_one({

        "student_id": student["_id"],

        "alumni_id": alumni["_id"]

    })



    if existing_connection:

        flash("Connection request already exists.", "error")

        return redirect(

            url_for(

                "alumni_profile",

                alumni_id=alumni_id

            )

        )



    connections_collection.insert_one({

        "student_id": student["_id"],

        "alumni_id": alumni["_id"],

        "college_id": student["college_id"],

        "status": "Pending"

    })



    flash(

        "Connection request sent successfully.",

        "success"

    )



    return redirect(

        url_for(

            "alumni_profile",

            alumni_id=alumni_id

        )

    )



@app.route("/student/connections")

def student_connections():



    if session.get("role") != "student":

        return redirect(url_for("login"))



    student = students_collection.find_one({

        "email": session.get("email")

    })



    if not student:

        flash("Student account not found.", "error")

        return redirect(url_for("logout"))



    connections_collection = db["connections"]



    connection_documents = list(

        connections_collection.find({

            "student_id": student["_id"]

        }).sort("_id", -1)

    )



    connections = []



    for connection in connection_documents:



        alumni = alumni_collection.find_one({

            "_id": connection.get("alumni_id"),

            "status": "Approved"

        })



        if alumni:



            connections.append({

                "alumni": alumni,

                "status": connection.get(

                    "status",

                    "Pending"

                )

            })



    return render_template(

        "connections.html",

        student=student,

        connections=connections

    )





# =========================================================

# LOGOUT

# =========================================================



@app.route("/logout")

def logout():

    email = session.get("email")
    role = session.get("role", "")

    if email:
        user = users_collection.find_one({"email": email})
        name = user.get("full_name", email) if user else email
        log_activity(
            "User logged out",
            f"{name} logged out.",
            name,
            role
        )

    session.clear()
    return redirect(url_for("home"))

@app.route("/alumni/dashboard")

def alumni_dashboard():



    if session.get("role") != "alumni":

        return redirect(url_for("login"))



    alumni = alumni_collection.find_one({

        "email": session.get("email")

    })



    if not alumni:

        flash("Alumni account not found.", "error")

        return redirect(url_for("logout"))



    # ================= COLLEGE =================



    college = colleges_collection.find_one({

        "_id": alumni.get("college_id")

    })



    # ================= CONNECTIONS =================



    connections_collection = db["connections"]



    total_connections = connections_collection.count_documents({

        "alumni_id": alumni["_id"],

        "status": "Accepted"

    })



    # ================= CONNECTION REQUESTS =================



    pending_documents = list(

        connections_collection.find({

            "alumni_id": alumni["_id"],

            "status": "Pending"

        }).sort("_id", -1)

    )



    pending_requests = len(pending_documents)



    connection_requests = []



    for connection in pending_documents:



        student = students_collection.find_one({

            "_id": connection.get("student_id")

        })



        if student:



            connection_requests.append({

                "id": str(connection["_id"]),

                "student": student

            })



    # ================= MENTORSHIP =================



    mentorship_collection = db["mentorship_requests"]



    pending_mentorship_documents = list(

        mentorship_collection.find({

            "alumni_id": alumni["_id"],

            "status": "Pending"

        }).sort("_id", -1)

    )



    mentorship_requests = len(

        pending_mentorship_documents

    )



    mentorship_request_list = []



    for mentorship in pending_mentorship_documents:



        student = students_collection.find_one({

            "_id": mentorship.get("student_id")

        })



        if student:



            mentorship_request_list.append({

                "id": str(mentorship["_id"]),

                "student": student

            })



    # ================= TASKS =================



    tasks_collection = db["tasks"]



    tasks_count = tasks_collection.count_documents({

        "alumni_id": alumni["_id"]

    })



    # ================= RENDER =================



    return render_template(

        "alumni_dashboard.html",

        alumni=alumni,

        college=college,

        total_connections=total_connections,

        pending_requests=pending_requests,

        connection_requests=connection_requests,

        mentorship_requests=mentorship_requests,

        mentorship_request_list=mentorship_request_list,

        tasks_count=tasks_count

    )

@app.route("/alumni/connections")
def alumni_connections():

    # =====================================================
    # CHECK LOGIN
    # =====================================================

    if "email" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    # =====================================================
    # CHECK ALUMNI ROLE
    # =====================================================

    if session.get("role") != "alumni":
        flash("You are not authorized to access Alumni Connections.", "error")

        # Send the user to their correct dashboard
        if session.get("role") == "student":
            return redirect(url_for("student_dashboard"))

        elif session.get("role") == "college_admin":
            return redirect(url_for("college_admin_dashboard"))

        elif session.get("role") == "platform_admin":
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("login"))

    # =====================================================
    # GET LOGGED-IN ALUMNI
    # =====================================================

    alumni = alumni_collection.find_one({
        "email": session.get("email")
    })

    if not alumni:
        flash("Alumni account not found.", "error")
        session.clear()
        return redirect(url_for("login"))

    # =====================================================
    # GET COLLEGE
    # =====================================================

    college = colleges_collection.find_one({
        "_id": alumni.get("college_id")
    })

    # =====================================================
    # CONNECTIONS COLLECTION
    # =====================================================

    connections_collection = db["connections"]

    # =====================================================
    # GET ALL CONNECTIONS FOR THIS ALUMNI
    # =====================================================

    connection_documents = list(
        connections_collection.find({
            "alumni_id": alumni["_id"]
        }).sort("_id", -1)
    )

    # =====================================================
    # SEPARATE PENDING AND ACCEPTED CONNECTIONS
    # =====================================================

    pending_requests = []
    accepted_connections = []

    for connection in connection_documents:

        student = students_collection.find_one({
            "_id": connection.get("student_id")
        })

        if not student:
            continue

        item = {
            "student": student,
            "connection": connection
        }

        status = connection.get("status", "Pending")

        # Handle both possible capitalization formats
        if str(status).lower() == "pending":

            pending_requests.append(item)

        elif str(status).lower() == "accepted":

            accepted_connections.append(item)

    # =====================================================
    # RENDER CONNECTIONS PAGE
    # =====================================================

    return render_template(
        "alumni_connections.html",
        alumni=alumni,
        college=college,
        pending_requests=pending_requests,
        accepted_connections=accepted_connections
    )
@app.route("/alumni/connection/accept/<connection_id>")

def accept_connection(connection_id):



    if session.get("role") != "alumni":

        return redirect(url_for("login"))



    alumni = alumni_collection.find_one({

        "email": session.get("email")

    })



    if not alumni:

        return redirect(url_for("logout"))



    try:



        connection_object_id = ObjectId(connection_id)



    except Exception:



        flash("Invalid connection request.", "error")



        return redirect(

            url_for("alumni_dashboard")

        )





    connections_collection = db["connections"]



    connection = connections_collection.find_one({

        "_id": connection_object_id,

        "alumni_id": alumni["_id"],

        "status": "Pending"

    })





    if not connection:



        flash(

            "Connection request not found.",

            "error"

        )



        return redirect(

            url_for("alumni_dashboard")

        )





    connections_collection.update_one(

        {"_id": connection_object_id},

        {

            "$set": {

                "status": "Accepted"

            }

        }

    )





    flash(

        "Connection request accepted.",

        "success"

    )



    return redirect(

        url_for("alumni_dashboard")

    )

@app.route("/alumni/connection/reject/<connection_id>")

def reject_connection(connection_id):



    if session.get("role") != "alumni":

        return redirect(url_for("login"))



    alumni = alumni_collection.find_one({

        "email": session.get("email")

    })



    if not alumni:

        return redirect(url_for("logout"))



    try:



        connection_object_id = ObjectId(connection_id)



    except Exception:



        flash("Invalid connection request.", "error")



        return redirect(

            url_for("alumni_dashboard")

        )





    connections_collection = db["connections"]



    connection = connections_collection.find_one({

        "_id": connection_object_id,

        "alumni_id": alumni["_id"],

        "status": "Pending"

    })





    if not connection:



        flash(

            "Connection request not found.",

            "error"

        )



        return redirect(

            url_for("alumni_dashboard")

        )





    connections_collection.update_one(

        {"_id": connection_object_id},

        {

            "$set": {

                "status": "Rejected"

            }

        }

    )





    flash(

        "Connection request rejected.",

        "success"

    )



    return redirect(

        url_for("alumni_dashboard")

    )

@app.route("/alumni/profile/edit", methods=["GET", "POST"])

def edit_alumni_profile():



    if session.get("role") != "alumni":

        return redirect(url_for("login"))



    alumni = alumni_collection.find_one({

        "email": session.get("email")

    })



    if not alumni:

        flash("Alumni account not found.", "error")

        return redirect(url_for("logout"))





    # ================= UPDATE PROFILE =================



    if request.method == "POST":



        full_name = request.form.get(

            "full_name", ""

        ).strip()



        phone = request.form.get(

            "phone", ""

        ).strip()



        current_location = request.form.get(

            "current_location", ""

        ).strip()



        department = request.form.get(

            "department", ""

        ).strip()



        degree = request.form.get(

            "degree", ""

        ).strip()



        graduation_year = request.form.get(

            "graduation_year", ""

        ).strip()



        job_title = request.form.get(

            "job_title", ""

        ).strip()



        company = request.form.get(

            "company", ""

        ).strip()



        industry = request.form.get(

            "industry", ""

        ).strip()



        experience = request.form.get(

            "experience", ""

        ).strip()



        skills = request.form.get(

            "skills", ""

        ).strip()



        linkedin = request.form.get(

            "linkedin", ""

        ).strip()



        github = request.form.get(

            "github", ""

        ).strip()



        portfolio = request.form.get(

            "portfolio", ""

        ).strip()



        mentorship = request.form.get(

            "mentorship", "no"

        )



        mentor_areas = request.form.get(

            "mentor_areas", ""

        ).strip()





        # ================= VALIDATION =================



        if not full_name:



            flash(

                "Full name is required.",

                "error"

            )



            return redirect(

                url_for("edit_alumni_profile")

            )





        # ================= UPDATE MONGODB =================



        alumni_collection.update_one(



            {

                "_id": alumni["_id"]

            },



            {

                "$set": {



                    "full_name": full_name,



                    "phone": phone,



                    "current_location":

                        current_location,



                    "department":

                        department,



                    "degree":

                        degree,



                    "graduation_year":

                        graduation_year,



                    "batch":

                        graduation_year,



                    "job_title":

                        job_title,



                    "company":

                        company,



                    "industry":

                        industry,



                    "experience":

                        experience,



                    "skills":

                        skills,



                    "linkedin":

                        linkedin,



                    "github":

                        github,



                    "portfolio":

                        portfolio,



                    "mentorship":

                        mentorship,



                    "mentor_areas":

                        mentor_areas



                }

            }

        )





        flash(

            "Profile updated successfully.",

            "success"

        )



        return redirect(

            url_for("alumni_dashboard")

        )





    # ================= DISPLAY FORM =================



    return render_template(

        "edit_alumni_profile.html",

        alumni=alumni

    )

@app.route("/messages")
def messages():

    # ---------------------------------------------------------
    # CHECK LOGIN
    # ---------------------------------------------------------
    if session.get("role") not in ["student", "alumni"]:
        return redirect(url_for("login"))

    # ---------------------------------------------------------
    # CURRENT USER
    # ---------------------------------------------------------
    current_user = users_collection.find_one({
        "email": session.get("email")
    })

    if not current_user:
        flash("User account not found.", "error")
        return redirect(url_for("logout"))

    current_user_id = current_user["_id"]

    contacts = []

    connections_collection = db["connections"]

    # Keep logged-in profiles separate
    student = None
    alumni = None

    # =========================================================
    # STUDENT
    # =========================================================
    if session.get("role") == "student":

        student = students_collection.find_one({
            "email": session.get("email")
        })

        if not student:
            flash("Student account not found.", "error")
            return redirect(url_for("logout"))

        connection_documents = list(
            connections_collection.find({
                "student_id": student["_id"],
                "status": "Accepted"
            }).sort("_id", -1)
        )

        # IMPORTANT:
        # Do not store the connected alumni in the
        # logged-in "alumni" variable.
        for connection in connection_documents:

            connected_alumni = alumni_collection.find_one({
                "_id": connection.get("alumni_id"),
                "status": "Approved"
            })

            if connected_alumni:

                contacts.append({
                    "id": str(connected_alumni["_id"]),
                    "name": connected_alumni.get(
                        "full_name",
                        "Alumni"
                    ),
                    "role": "Alumni"
                })

    # =========================================================
    # ALUMNI
    # =========================================================
    elif session.get("role") == "alumni":

        alumni = alumni_collection.find_one({
            "email": session.get("email")
        })

        if not alumni:
            flash("Alumni account not found.", "error")
            return redirect(url_for("logout"))

        connection_documents = list(
            connections_collection.find({
                "alumni_id": alumni["_id"],
                "status": "Accepted"
            }).sort("_id", -1)
        )

        # IMPORTANT:
        # Do not overwrite the logged-in alumni variable.
        for connection in connection_documents:

            connected_student = students_collection.find_one({
                "_id": connection.get("student_id")
            })

            if connected_student:

                contacts.append({
                    "id": str(connected_student["_id"]),
                    "name": connected_student.get(
                        "full_name",
                        "Student"
                    ),
                    "role": "Student"
                })

    # =========================================================
    # SELECTED CONTACT
    # =========================================================

    selected_user_id = request.args.get("user_id")

    selected_contact = None
    chat_messages = []

    if selected_user_id:

        try:

            selected_object_id = ObjectId(selected_user_id)

        except Exception:

            flash("Invalid contact.", "error")

            return redirect(
                url_for("messages")
            )

        # Check whether selected user is an accepted connection
        for contact in contacts:

            if contact["id"] == selected_user_id:

                selected_contact = contact
                break

        if not selected_contact:

            flash(
                "You can only message accepted connections.",
                "error"
            )

            return redirect(
                url_for("messages")
            )

        # -----------------------------------------------------
        # GET CHAT MESSAGES
        # -----------------------------------------------------

        messages_collection = db["messages"]

        chat_messages = list(
            messages_collection.find({

                "$or": [

                    {
                        "sender_id": current_user_id,
                        "receiver_id": selected_object_id
                    },

                    {
                        "sender_id": selected_object_id,
                        "receiver_id": current_user_id
                    }

                ]

            }).sort("created_at", 1)
        )

    # =========================================================
    # PROFILE USER
    # =========================================================

    profile_user = student if student is not None else alumni

    # =========================================================
    # RENDER
    # =========================================================

    return render_template(
        "messages.html",

        student=student,

        alumni=alumni,

        profile_user=profile_user,

        contacts=contacts,

        selected_user_id=selected_user_id,

        selected_contact=selected_contact,

        chat_messages=chat_messages,

        current_user_id=current_user_id
    )

@app.route(

    "/messages/send/<user_id>",

    methods=["POST"]

)

def send_message(user_id):



    if session.get("role") not in [

        "student",

        "alumni"

    ]:

        return redirect(url_for("login"))





    current_user = users_collection.find_one({

        "email": session.get("email")

    })



    if not current_user:

        flash(

            "User account not found.",

            "error"

        )



        return redirect(

            url_for("logout")

        )





    try:



        receiver_id = ObjectId(user_id)



    except Exception:



        flash(

            "Invalid receiver.",

            "error"

        )



        return redirect(

            url_for("messages")

        )





    message_text = request.form.get(

        "message",

        ""

    ).strip()





    if not message_text:



        flash(

            "Message cannot be empty.",

            "error"

        )



        return redirect(

            url_for(

                "messages",

                user_id=user_id

            )

        )





    current_user_id = current_user["_id"]





    # =====================================================

    # VERIFY ACCEPTED CONNECTION

    # =====================================================



    connections_collection = db["connections"]



    if session.get("role") == "student":



        student = students_collection.find_one({

            "email": session.get("email")

        })



        if not student:

            return redirect(

                url_for("logout")

            )



        connection = connections_collection.find_one({

            "student_id": student["_id"],

            "alumni_id": receiver_id,

            "status": "Accepted"

        })





    else:



        alumni = alumni_collection.find_one({

            "email": session.get("email")

        })



        if not alumni:

            return redirect(

                url_for("logout")

            )



        connection = connections_collection.find_one({

            "alumni_id": alumni["_id"],

            "student_id": receiver_id,

            "status": "Accepted"

        })





    if not connection:



        flash(

            "You can only message accepted connections.",

            "error"

        )



        return redirect(

            url_for("messages")

        )





    # =====================================================

    # SAVE MESSAGE

    # =====================================================



    messages_collection = db["messages"]



    messages_collection.insert_one({



        "sender_id": current_user_id,



        "receiver_id": receiver_id,



        "message": message_text,



        "created_at": datetime.now()



    })





    return redirect(

        url_for(

            "messages",

            user_id=user_id

        )

    )

@app.route("/student/mentorship/request/<alumni_id>")

def request_mentorship(alumni_id):



    if session.get("role") != "student":

        return redirect(url_for("login"))





    student = students_collection.find_one({

        "email": session.get("email")

    })





    if not student:



        flash(

            "Student account not found.",

            "error"

        )



        return redirect(

            url_for("logout")

        )





    try:



        alumni_object_id = ObjectId(alumni_id)



    except Exception:



        flash(

            "Invalid alumni.",

            "error"

        )



        return redirect(

            url_for("find_alumni")

        )





    # ================= FIND ALUMNI =================



    alumni = alumni_collection.find_one({



        "_id": alumni_object_id,



        "status": "Approved"



    })





    if not alumni:



        flash(

            "Alumni not found.",

            "error"

        )



        return redirect(

            url_for("find_alumni")

        )





    # ================= COLLEGE CHECK =================



    if alumni.get("college_id") != student.get(

        "college_id"

    ):



        flash(

            "You cannot request mentorship from this alumni.",

            "error"

        )



        return redirect(

            url_for(

                "alumni_profile",

                alumni_id=alumni_id

            )

        )





    # ================= MENTOR CHECK =================



    if alumni.get("mentorship") != "yes":



        flash(

            "This alumni is not currently available for mentorship.",

            "error"

        )



        return redirect(

            url_for(

                "alumni_profile",

                alumni_id=alumni_id

            )

        )





    mentorship_collection = db[

        "mentorship_requests"

    ]





    # ================= EXISTING REQUEST =================



    existing_request = mentorship_collection.find_one({



        "student_id": student["_id"],



        "alumni_id": alumni["_id"]



    })





    if existing_request:



        flash(

            "Mentorship request already exists.",

            "error"

        )



        return redirect(

            url_for(

                "alumni_profile",

                alumni_id=alumni_id

            )

        )





    # ================= CREATE REQUEST =================



    mentorship_collection.insert_one({



        "student_id": student["_id"],



        "alumni_id": alumni["_id"],



        "college_id": student["college_id"],



        "status": "Pending"



    })





    log_activity(
        "Mentorship requested",
        f"{current_user_name()} sent a mentorship request.",
        current_user_name(),
        "student"
    )

    flash(

        "Mentorship request sent successfully.",

        "success"

    )





    return redirect(

        url_for(

            "alumni_profile",

            alumni_id=alumni_id

        )

    )

@app.route(

    "/alumni/mentorship/accept/<request_id>"

)

def accept_mentorship(request_id):



    if session.get("role") != "alumni":

        return redirect(url_for("login"))





    alumni = alumni_collection.find_one({

        "email": session.get("email")

    })





    if not alumni:



        return redirect(

            url_for("logout")

        )





    try:



        request_object_id = ObjectId(

            request_id

        )



    except Exception:



        flash(

            "Invalid mentorship request.",

            "error"

        )



        return redirect(

            url_for("alumni_dashboard")

        )





    mentorship_collection = db[

        "mentorship_requests"

    ]





    mentorship = mentorship_collection.find_one({



        "_id": request_object_id,



        "alumni_id": alumni["_id"],



        "status": "Pending"



    })





    if not mentorship:



        flash(

            "Mentorship request not found.",

            "error"

        )



        return redirect(

            url_for("alumni_dashboard")

        )





    mentorship_collection.update_one(



        {

            "_id": request_object_id

        },



        {

            "$set": {

                "status": "Accepted"

            }

        }



    )





    flash(

        "Mentorship request accepted.",

        "success"

    )





    return redirect(

        url_for("alumni_dashboard")

    )

@app.route(

    "/alumni/mentorship/reject/<request_id>"

)

def reject_mentorship(request_id):



    if session.get("role") != "alumni":

        return redirect(url_for("login"))





    alumni = alumni_collection.find_one({

        "email": session.get("email")

    })





    if not alumni:



        return redirect(

            url_for("logout")

        )





    try:



        request_object_id = ObjectId(

            request_id

        )



    except Exception:



        flash(

            "Invalid mentorship request.",

            "error"

        )



        return redirect(

            url_for("alumni_dashboard")

        )





    mentorship_collection = db[

        "mentorship_requests"

    ]





    mentorship = mentorship_collection.find_one({



        "_id": request_object_id,



        "alumni_id": alumni["_id"],



        "status": "Pending"



    })





    if not mentorship:



        flash(

            "Mentorship request not found.",

            "error"

        )



        return redirect(

            url_for("alumni_dashboard")

        )





    mentorship_collection.update_one(



        {

            "_id": request_object_id

        },



        {

            "$set": {

                "status": "Rejected"

            }

        }



    )





    flash(

        "Mentorship request rejected.",

        "success"

    )





    return redirect(

        url_for("alumni_dashboard")

    )
@app.route("/college-admin/student/approve/<student_id>")
def college_admin_approve_student(student_id):
    if session.get("role") != "college_admin": return redirect(url_for("login"))
    if not ObjectId.is_valid(str(student_id)):
        flash("Invalid student ID.", "error"); return redirect(url_for("college_admin_dashboard"))
    student = students_collection.find_one({"_id": ObjectId(str(student_id))})
    if not student: flash("Student not found.", "error"); return redirect(url_for("college_admin_dashboard"))
    admin = users_collection.find_one({"email": session.get("email"), "role": "college_admin"})
    if not admin: flash("College admin account not found.", "error"); return redirect(url_for("login"))
    college_id = admin.get("college_id")
    if not college_id:
        college = colleges_collection.find_one({"admin_email": session.get("email")})
        if not college: flash("College Admin is not linked to a college.", "error"); return redirect(url_for("college_admin_dashboard"))
        college_id = college["_id"]
        users_collection.update_one({"_id": admin["_id"]}, {"$set": {"college_id": college_id, "college_name": college.get("college_name"), "college_code": college.get("college_code")}})
    if isinstance(college_id, str):
        if not ObjectId.is_valid(college_id): flash("Invalid college ID.", "error"); return redirect(url_for("college_admin_dashboard"))
        college_id = ObjectId(college_id)
    if str(student.get("college_id")) != str(college_id): flash("Unauthorized action. Student belongs to another college.", "error"); return redirect(url_for("college_admin_dashboard"))
    students_collection.update_one({"_id": student["_id"]}, {"$set": {"status": "Approved", "college_id": college_id}})
    users_collection.update_one({"email": student.get("email"), "role": "student"}, {"$set": {"status": "Active", "college_id": college_id}})
    flash("Student approved successfully.", "success")
    return redirect(url_for("college_admin_dashboard"))

@app.route("/college-admin/student/reject/<student_id>")
def college_admin_reject_student(student_id):
    if session.get("role") != "college_admin": return redirect(url_for("login"))
    if not ObjectId.is_valid(str(student_id)):
        flash("Invalid student ID.", "error"); return redirect(url_for("college_admin_dashboard"))
    student = students_collection.find_one({"_id": ObjectId(str(student_id))})
    if not student: flash("Student not found.", "error"); return redirect(url_for("college_admin_dashboard"))
    admin = users_collection.find_one({"email": session.get("email"), "role": "college_admin"})
    if not admin: flash("College admin account not found.", "error"); return redirect(url_for("login"))
    college_id = admin.get("college_id")
    if not college_id:
        college = colleges_collection.find_one({"admin_email": session.get("email")})
        if not college: flash("College Admin is not linked to a college.", "error"); return redirect(url_for("college_admin_dashboard"))
        college_id = college["_id"]
        users_collection.update_one({"_id": admin["_id"]}, {"$set": {"college_id": college_id, "college_name": college.get("college_name"), "college_code": college.get("college_code")}})
    if isinstance(college_id, str):
        if not ObjectId.is_valid(college_id): flash("Invalid college ID.", "error"); return redirect(url_for("college_admin_dashboard"))
        college_id = ObjectId(college_id)
    if str(student.get("college_id")) != str(college_id): flash("Unauthorized action. Student belongs to another college.", "error"); return redirect(url_for("college_admin_dashboard"))
    students_collection.update_one({"_id": student["_id"]}, {"$set": {"status": "Rejected"}})
    users_collection.update_one({"email": student.get("email"), "role": "student"}, {"$set": {"status": "Rejected"}})
    flash("Student registration rejected.", "success")
    return redirect(url_for("college_admin_dashboard"))

# =========================================================
# APPROVE ALUMNI
# =========================================================

@app.route("/college-admin/approve-alumni/<alumni_id>")
def college_admin_approve_alumni(alumni_id):
    if session.get("role") != "college_admin": return redirect(url_for("login"))
    if not ObjectId.is_valid(str(alumni_id)):
        flash("Invalid alumni ID.", "error"); return redirect(url_for("college_admin_dashboard"))
    alumni = alumni_collection.find_one({"_id": ObjectId(str(alumni_id))})
    if not alumni: flash("Alumni not found.", "error"); return redirect(url_for("college_admin_dashboard"))
    admin = users_collection.find_one({"email": session.get("email"), "role": "college_admin"})
    if not admin: flash("College admin account not found.", "error"); return redirect(url_for("login"))
    college_id = admin.get("college_id")
    if not college_id:
        college = colleges_collection.find_one({"admin_email": session.get("email")})
        if not college: flash("College Admin is not linked to a college.", "error"); return redirect(url_for("college_admin_dashboard"))
        college_id = college["_id"]
        users_collection.update_one({"_id": admin["_id"]}, {"$set": {"college_id": college_id, "college_name": college.get("college_name"), "college_code": college.get("college_code")}})
    if isinstance(college_id, str):
        if not ObjectId.is_valid(college_id): flash("Invalid college ID.", "error"); return redirect(url_for("college_admin_dashboard"))
        college_id = ObjectId(college_id)
    alumni_college_id = alumni.get("college_id")
    if not alumni_college_id:
        alumni_collection.update_one({"_id": alumni["_id"]}, {"$set": {"college_id": college_id}})
        alumni_college_id = college_id
    if str(alumni_college_id) != str(college_id):
        flash("Unauthorized action. Alumni belongs to another college.", "error"); return redirect(url_for("college_admin_dashboard"))
    alumni_collection.update_one({"_id": alumni["_id"]}, {"$set": {"status": "Approved", "college_id": college_id}})
    users_collection.update_one({"email": alumni.get("email"), "role": "alumni"}, {"$set": {"status": "Active", "college_id": college_id}})
    log_activity("Alumni approved", f"{alumni.get('full_name', 'Alumni')} was approved.", alumni.get("full_name", "Alumni"), "college_admin")
    flash("Alumni approved successfully.", "success")
    return redirect(url_for("college_admin_dashboard"))



# ============================================================
# COLLEGE ADMIN - STUDENTS
# ============================================================

@app.route("/college-admin/students")
def college_admin_students():

    if session.get("role") != "college_admin":
        return redirect(url_for("login"))

    # Get logged-in college admin
    college_admin = users_collection.find_one({
        "email": session.get("email"),
        "role": "college_admin"
    })

    if not college_admin:
        flash("College admin account not found.", "error")
        return redirect(url_for("logout"))

    college_id = college_admin.get("college_id")

    # Get college
    college = colleges_collection.find_one({
        "_id": college_id
    })

    if not college:
        flash("College information not found.", "error")
        return redirect(url_for("logout"))

    # Search
    search = request.args.get("search", "").strip()

    # Status filter
    status = request.args.get("status", "").strip()

    query = {
        "college_id": college_id
    }

    # Search by name, email or department
    if search:
        query["$or"] = [
            {
                "full_name": {
                    "$regex": search,
                    "$options": "i"
                }
            },
            {
                "email": {
                    "$regex": search,
                    "$options": "i"
                }
            },
            {
                "department": {
                    "$regex": search,
                    "$options": "i"
                }
            }
        ]

    # Status filter
    if status:
        query["status"] = status

    students = list(
        students_collection.find(query)
        .sort("_id", -1)
    )

    return render_template(
        "college_students.html",
        college=college,
        college_admin=college_admin,
        students=students,
        search=search,
        selected_status=status
    )

@app.route("/student/mentorship")
def student_mentorship():

    if session.get("role") != "student":
        return redirect(url_for("login"))

    student = students_collection.find_one({
        "email": session.get("email")
    })

    if not student:
        flash("Student account not found.", "error")
        return redirect(url_for("logout"))

    college = colleges_collection.find_one({
        "_id": student.get("college_id")
    })

    mentorship_collection = db["mentorship_requests"]

    # Get all approved mentors from the same college
    mentors = list(
        alumni_collection.find({
            "college_id": student.get("college_id"),
            "status": "Approved",
            "mentorship": "yes"
        }).sort("full_name", 1)
    )

    # Get student's existing mentorship requests
    mentorship_requests = list(
        mentorship_collection.find({
            "student_id": student["_id"]
        }).sort("_id", -1)
    )

    # Add request status to each mentor
    for mentor in mentors:

        request = mentorship_collection.find_one({
            "student_id": student["_id"],
            "alumni_id": mentor["_id"]
        })

        mentor["mentorship_status"] = (
            request.get("status")
            if request
            else None
        )

    return render_template(
        "student_mentorship.html",
        student=student,
        college=college,
        mentors=mentors,
        mentorship_requests=mentorship_requests
    )
@app.route("/student/tasks")
def student_tasks():

    if session.get("role") != "student":
        return redirect(url_for("login"))

    student = students_collection.find_one({
        "email": session.get("email")
    })

    if not student:
        flash("Student account not found.", "error")
        return redirect(url_for("logout"))

    college = colleges_collection.find_one({
        "_id": student.get("college_id")
    })

    tasks_collection = db["tasks"]

    tasks = list(
        tasks_collection.find({
            "student_id": student["_id"]
        }).sort("_id", -1)
    )

    pending_tasks = []
    in_progress_tasks = []
    completed_tasks = []

    for task in tasks:

        status = task.get("status", "Pending")

        if status == "Completed":
            completed_tasks.append(task)

        elif status == "In Progress":
            in_progress_tasks.append(task)

        else:
            pending_tasks.append(task)

    return render_template(
        "student_tasks.html",
        student=student,
        college=college,
        pending_tasks=pending_tasks,
        in_progress_tasks=in_progress_tasks,
        completed_tasks=completed_tasks
    )
@app.route("/student/tasks/start/<task_id>")
def start_task(task_id):

    if session.get("role") != "student":
        return redirect(url_for("login"))

    student = students_collection.find_one({
        "email": session.get("email")
    })

    if not student:
        flash("Student account not found.", "error")
        return redirect(url_for("logout"))

    if not ObjectId.is_valid(task_id):
        flash("Invalid task.", "error")
        return redirect(url_for("student_tasks"))

    tasks_collection = db["tasks"]

    task = tasks_collection.find_one({
        "_id": ObjectId(task_id),
        "student_id": student["_id"]
    })

    if not task:
        flash("Task not found.", "error")
        return redirect(url_for("student_tasks"))

    tasks_collection.update_one(
        {
            "_id": ObjectId(task_id),
            "student_id": student["_id"]
        },
        {
            "$set": {
                "status": "In Progress"
            }
        }
    )

    flash("Task started.", "success")

    return redirect(url_for("student_tasks"))
@app.route("/student/tasks/complete/<task_id>")
def complete_task(task_id):

    if session.get("role") != "student":
        return redirect(url_for("login"))

    student = students_collection.find_one({
        "email": session.get("email")
    })

    if not student:
        flash("Student account not found.", "error")
        return redirect(url_for("logout"))

    if not ObjectId.is_valid(task_id):
        flash("Invalid task.", "error")
        return redirect(url_for("student_tasks"))

    tasks_collection = db["tasks"]

    task = tasks_collection.find_one({
        "_id": ObjectId(task_id),
        "student_id": student["_id"]
    })

    if not task:
        flash("Task not found.", "error")
        return redirect(url_for("student_tasks"))

    tasks_collection.update_one(
        {
            "_id": ObjectId(task_id),
            "student_id": student["_id"]
        },
        {
            "$set": {
                "status": "Completed"
            }
        }
    )

    flash("Task marked as completed.", "success")

    return redirect(url_for("student_tasks"))
@app.route("/student/tasks/delete/<task_id>")
def delete_task(task_id):

    if session.get("role") != "student":
        return redirect(url_for("login"))

    student = students_collection.find_one({
        "email": session.get("email")
    })

    if not student:
        flash("Student account not found.", "error")
        return redirect(url_for("logout"))

    if not ObjectId.is_valid(task_id):
        flash("Invalid task.", "error")
        return redirect(url_for("student_tasks"))

    tasks_collection = db["tasks"]

    result = tasks_collection.delete_one({
        "_id": ObjectId(task_id),
        "student_id": student["_id"]
    })

    if result.deleted_count:
        flash("Task deleted.", "success")
    else:
        flash("Task not found.", "error")

    return redirect(url_for("student_tasks"))

@app.route("/admin/delete-college/<college_id>")
def admin_delete_college(college_id):

    # Only Platform Admin can delete colleges
    if session.get("role") != "platform_admin":
        flash("Unauthorized access.", "error")
        return redirect(url_for("login"))

    # Validate college ID
    if not ObjectId.is_valid(str(college_id)):
        flash("Invalid college ID.", "error")
        return redirect(url_for("admin_dashboard"))

    college = colleges_collection.find_one({
        "_id": ObjectId(str(college_id))
    })

    if not college:
        flash("College not found.", "error")
        return redirect(url_for("admin_dashboard"))

    college_id_obj = college["_id"]

    # Delete college
    colleges_collection.delete_one({
        "_id": college_id_obj
    })

    # Delete college admin account
    users_collection.delete_many({
        "college_id": college_id_obj,
        "role": "college_admin"
    })

    # Delete students belonging to this college
    students_collection.delete_many({
        "college_id": college_id_obj
    })

    # Delete alumni belonging to this college
    alumni_collection.delete_many({
        "college_id": college_id_obj
    })

    # Delete related connections
    db["connections"].delete_many({
        "college_id": college_id_obj
    })

    # Delete related announcements
    db["announcements"].delete_many({
        "college_id": college_id_obj
    })

    # Delete related tasks
    db["tasks"].delete_many({
        "college_id": college_id_obj
    })

    # Delete mentorship requests
    db["mentorship_requests"].delete_many({
        "college_id": college_id_obj
    })

    flash(
        f"{college.get('college_name', 'College')} removed successfully.",
        "success"
    )

    return redirect(url_for("admin_dashboard"))

# =========================================================
# ALUMNI - TASK MANAGEMENT
# =========================================================

@app.route("/alumni/tasks", methods=["GET", "POST"])
def alumni_tasks():

    if session.get("role") != "alumni":
        return redirect(url_for("login"))

    # -----------------------------------------------------
    # Logged-in alumni
    # -----------------------------------------------------

    alumni = alumni_collection.find_one({
        "email": session.get("email")
    })

    if not alumni:
        flash("Alumni account not found.", "error")
        return redirect(url_for("logout"))

    # -----------------------------------------------------
    # Get college
    # -----------------------------------------------------

    college = colleges_collection.find_one({
        "_id": alumni.get("college_id")
    })

    # -----------------------------------------------------
    # Get ONLY accepted connected students
    # -----------------------------------------------------

    connections_collection = db["connections"]

    accepted_connections = list(
        connections_collection.find({
            "alumni_id": alumni["_id"],
            "status": "Accepted"
        }).sort("_id", -1)
    )

    connected_students = []

    for connection in accepted_connections:

        student = students_collection.find_one({
            "_id": connection.get("student_id"),
            "college_id": alumni.get("college_id"),
            "status": "Approved"
        })

        if student:
            connected_students.append(student)

    # -----------------------------------------------------
    # Create task
    # -----------------------------------------------------

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = request.form.get("due_date", "").strip()
        priority = request.form.get("priority", "Medium").strip()

        student_ids = request.form.getlist("student_ids")

        if not title:
            flash("Task title is required.", "error")
            return redirect(url_for("alumni_tasks"))

        if not description:
            flash("Task description is required.", "error")
            return redirect(url_for("alumni_tasks"))

        if not student_ids:
            flash("Please select at least one connected student.", "error")
            return redirect(url_for("alumni_tasks"))

        tasks_collection = db["tasks"]

        assigned_count = 0

        for student_id in student_ids:

            if not ObjectId.is_valid(student_id):
                continue

            student = students_collection.find_one({
                "_id": ObjectId(student_id),
                "status": "Approved",
                "college_id": alumni.get("college_id")
            })

            # Make sure student is actually connected
            connection = connections_collection.find_one({
                "alumni_id": alumni["_id"],
                "student_id": ObjectId(student_id),
                "status": "Accepted"
            })

            if not student or not connection:
                continue

            tasks_collection.insert_one({
                "title": title,
                "description": description,
                "due_date": due_date,
                "priority": priority,

                "alumni_id": alumni["_id"],
                "student_id": student["_id"],
                "college_id": alumni.get("college_id"),

                "status": "Pending",

                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })

            assigned_count += 1

        if assigned_count == 0:
            flash(
                "Task could not be assigned to the selected students.",
                "error"
            )
        else:
            flash(
                f"Task assigned successfully to {assigned_count} student(s).",
                "success"
            )

        return redirect(url_for("alumni_tasks"))

    # -----------------------------------------------------
    # Get alumni's tasks
    # -----------------------------------------------------

    tasks_collection = db["tasks"]

    tasks = list(
        tasks_collection.find({
            "alumni_id": alumni["_id"]
        }).sort("_id", -1)
    )

    # Add student information to each task
    for task in tasks:

        student = students_collection.find_one({
            "_id": task.get("student_id")
        })

        task["student"] = student

    return render_template(
        "alumni_tasks.html",
        alumni=alumni,
        college=college,
        connected_students=connected_students,
        tasks=tasks
    )
@app.route("/alumni/tasks/edit/<task_id>", methods=["GET", "POST"])
def edit_alumni_task(task_id):

    if session.get("role") != "alumni":
        return redirect(url_for("login"))

    if not ObjectId.is_valid(task_id):
        flash("Invalid task.", "error")
        return redirect(url_for("alumni_tasks"))

    alumni = alumni_collection.find_one({
        "email": session.get("email")
    })

    if not alumni:
        flash("Alumni account not found.", "error")
        return redirect(url_for("logout"))

    tasks_collection = db["tasks"]

    task = tasks_collection.find_one({
        "_id": ObjectId(task_id),
        "alumni_id": alumni["_id"]
    })

    if not task:
        flash("Task not found or unauthorized access.", "error")
        return redirect(url_for("alumni_tasks"))

    # -----------------------------------------------------
    # Connected students
    # -----------------------------------------------------

    connections_collection = db["connections"]

    accepted_connections = list(
        connections_collection.find({
            "alumni_id": alumni["_id"],
            "status": "Accepted"
        })
    )

    connected_students = []

    for connection in accepted_connections:

        student = students_collection.find_one({
            "_id": connection.get("student_id"),
            "college_id": alumni.get("college_id"),
            "status": "Approved"
        })

        if student:
            connected_students.append(student)

    # -----------------------------------------------------
    # Update task
    # -----------------------------------------------------

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = request.form.get("due_date", "").strip()
        priority = request.form.get("priority", "Medium").strip()
        student_id = request.form.get("student_id", "").strip()

        if not title or not description:
            flash(
                "Task title and description are required.",
                "error"
            )
            return redirect(
                url_for(
                    "edit_alumni_task",
                    task_id=task_id
                )
            )

        if not ObjectId.is_valid(student_id):
            flash("Invalid student.", "error")
            return redirect(
                url_for(
                    "edit_alumni_task",
                    task_id=task_id
                )
            )

        # Make sure student is connected
        connection = connections_collection.find_one({
            "alumni_id": alumni["_id"],
            "student_id": ObjectId(student_id),
            "status": "Accepted"
        })

        if not connection:
            flash(
                "You can only assign tasks to connected students.",
                "error"
            )
            return redirect(
                url_for(
                    "edit_alumni_task",
                    task_id=task_id
                )
            )

        tasks_collection.update_one(
            {
                "_id": ObjectId(task_id),
                "alumni_id": alumni["_id"]
            },
            {
                "$set": {
                    "title": title,
                    "description": description,
                    "due_date": due_date,
                    "priority": priority,
                    "student_id": ObjectId(student_id),
                    "updated_at": datetime.now()
                }
            }
        )

        flash(
            "Task updated successfully.",
            "success"
        )

        return redirect(url_for("alumni_tasks"))

    return render_template(
        "edit_alumni_task.html",
        alumni=alumni,
        task=task,
        connected_students=connected_students
    )
@app.route("/alumni/tasks/delete/<task_id>", methods=["POST"])
def delete_alumni_task(task_id):

    if session.get("role") != "alumni":
        return redirect(url_for("login"))

    if not ObjectId.is_valid(task_id):
        flash("Invalid task.", "error")
        return redirect(url_for("alumni_tasks"))

    alumni = alumni_collection.find_one({
        "email": session.get("email")
    })

    if not alumni:
        flash("Alumni account not found.", "error")
        return redirect(url_for("logout"))

    tasks_collection = db["tasks"]

    result = tasks_collection.delete_one({
        "_id": ObjectId(task_id),
        "alumni_id": alumni["_id"]
    })

    if result.deleted_count:

        flash(
            "Task deleted successfully.",
            "success"
        )

    else:

        flash(
            "Task not found or unauthorized access.",
            "error"
        )

    return redirect(url_for("alumni_tasks"))

# =========================================================

# RUN

# =========================================================



if __name__ == "__main__":

    app.run(

        debug=True,

        host="0.0.0.0"

    )
