# College Alumni Portal

## About the Project

The **College Alumni Portal** is a web application that connects current students and alumni of a college.

Students can find alumni, send connection requests, communicate with them, and request mentorship. Alumni can connect with students and provide guidance.

The system also allows college administrators to manage students and alumni.

---

## Features

### Platform Admin
- Manage colleges
- Approve or reject college registrations
- Manage users
- Send announcements

### College Admin
- View college dashboard
- Approve or reject student registrations
- Approve or reject alumni registrations
- Manage students and alumni
- Suspend or activate users
- Delete users
- Send announcements

### Student
- Register and login
- Find alumni
- View alumni profiles
- Send connection requests
- Manage connections
- Send messages
- Request mentorship
- View tasks

### Alumni
- Register and login
- Manage profile
- Receive connection requests
- Accept or reject connections
- Communicate with students
- Provide mentorship
- Accept or reject mentorship requests
- View tasks

---

## Technologies Used

- HTML
- CSS
- JavaScript
- Python
- Flask
- MongoDB
- PyMongo
- Jinja2
- Git
- GitHub
- Visual Studio Code

---

## System Workflow

```text
College Registration
        ↓
Platform Admin Approval
        ↓
Approved College
        ↓
Student / Alumni Registration
        ↓
College Admin Approval
        ↓
Student / Alumni Dashboard
        ↓
Find Alumni
        ↓
Connection Request
        ↓
Accept Connection
        ↓
Messaging / Mentorship

Project Structure
College-Alumni-Portal/
│
├── app.py
├── requirements.txt
├── .gitignore
├── README.md
│
├── static/
│   └── style.css
│
└── templates/
    ├── index.html
    ├── login.html
    ├── register_college.html
    ├── register_student.html
    ├── register_alumni.html
    ├── admin_dashboard.html
    ├── college_dashboard.html
    ├── student_dashboard.html
    ├── find_alumni.html
    ├── alumni_profile.html
    ├── connections.html
    ├── messages.html
    ├── student_mentorship.html
    └── student_tasks.html

How to Run
1. Clone the Repository
git clone https://github.com/kiruthikabalamurugan05/College-Alumni-Portal.git

2. Open the Project
cd College-Alumni-Portal

3. Create a Virtual Environment
python -m venv venv

4. Activate the Virtual Environment
For Windows:
venv\Scripts\activate

5. Install Required Packages
pip install -r requirements.txt

6. Start MongoDB
Make sure MongoDB is running on your system.
7. Run the Application
python app.py

8. Open in Browser
http://127.0.0.1:5000

User Roles
Role	Main Responsibility
Platform Admin	Manage colleges and users
College Admin	Manage students and alumni
Student	Find and connect with alumni
Alumni	Connect with students and provide mentorship


Future Improvements
- Real-time chat
- Email notifications
- Alumni events
- Job and internship opportunities
- Mobile application
- Analytics and reports
Author
Kiruthika B
B.Tech Information Technology
