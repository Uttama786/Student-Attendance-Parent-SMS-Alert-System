# 🎓 AttendEase — Student Attendance & Parent SMS Alert System

A production-ready **Flask** web application for managing student attendance and automatically notifying parents via **Twilio SMS** whenever a student is marked absent.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔐 Authentication | Admin & Faculty login with hashed passwords, session management, CSRF protection |
| 👨‍🎓 Student Management | Full CRUD — Add, Edit, Delete students with parent contact info |
| ✅ Attendance Marking | Subject-wise, date-wise attendance with Present/Absent toggle and bulk actions |
| 📱 SMS Alerts | Twilio SMS sent automatically when a student is marked Absent |
| 📊 Dashboard | KPI cards + 7-day trend chart + today's doughnut chart |
| 📋 Reports | Daily report, per-student history with attendance % |
| 📥 Export | Excel (.xlsx) and PDF downloads for daily reports |
| 🔑 SMS Log | Full audit trail of every SMS attempt with Twilio SID |
| 👥 Faculty Management | Admin can add/delete faculty accounts |

---

## 🗂️ Project Structure

```
app/
├── app.py                    # App factory & entry point
├── config.py                 # Configuration from .env
├── extensions.py             # SQLAlchemy, LoginManager, CSRF
├── models.py                 # ORM models
├── requirements.txt
├── .env.example
│
├── blueprints/
│   ├── auth/routes.py        # /login  /logout
│   ├── dashboard/routes.py   # /
│   ├── students/routes.py    # /students/…
│   ├── attendance/routes.py  # /attendance/…
│   ├── sms/service.py        # Twilio SMS helper
│   └── reports/routes.py     # /reports/…
│
├── templates/
│   ├── base.html
│   ├── auth/login.html
│   ├── dashboard/index.html
│   ├── students/{list,form}.html
│   ├── attendance/{mark,history,sms_log}.html
│   └── reports/{daily,student,faculty}.html
│
└── static/
    ├── css/custom.css        # Dark premium theme
    └── js/app.js             # Sidebar, DataTables, CSRF helper
```

---

## 🚀 Quick Start

### 1. Clone / open the project

```powershell
cd c:\Users\AIML\Desktop\app
```

### 2. Create a virtual environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment

```powershell
copy .env.example .env
# Edit .env with your Twilio credentials and a strong SECRET_KEY
notepad .env
```

### 5. Run the application

```powershell
python app.py
```

Open **http://localhost:5000** in your browser.

### 6. Default Login

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `Admin@123` |

---

## 📱 Twilio SMS Configuration

1. Sign up at [https://www.twilio.com/](https://www.twilio.com/) (free trial available)
2. Navigate to **Console → Account Info** to get your:
   - **Account SID** (starts with `AC…`)
   - **Auth Token**
3. Get a **Twilio phone number** from **Phone Numbers → Manage → Buy a number**
4. Add them to your `.env` file:

```ini
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+1234567890
```

> **Without Twilio configured**, the system falls back to **console logging** — SMS messages are printed to the terminal instead of being sent. This is perfect for development.

### SMS Format

```
Dear Parent,
Your child {student_name} was absent for {subject_name} on {date}.
Please contact the college if required.
— Attendance Management System
```

---

## 🗄️ Database

The app uses **SQLite** by default (file: `attendance.db`). No setup required.

To switch to **MySQL**:

```ini
# .env
DATABASE_URL=mysql+pymysql://user:password@localhost/attendance_db
```

Install the MySQL driver:

```bash
pip install PyMySQL
```

### Tables

| Table | Description |
|---|---|
| `faculty` | System users (admin / faculty roles) |
| `students` | Student profiles with parent contact |
| `attendance` | Per-subject, per-day attendance records |
| `sms_log` | Full SMS audit log with Twilio SID |

---

## 🔒 Security Features

- **Password hashing** via Werkzeug `generate_password_hash / check_password_hash`
- **CSRF protection** on all forms via Flask-WTF
- **SQL injection protection** via SQLAlchemy ORM parameterised queries
- **Login required** decorator on all protected routes
- **Role-based access** — admin-only routes (delete student, faculty management)
- **Input validation** via WTForms validators

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| Flask | Web framework |
| Flask-SQLAlchemy | ORM & DB management |
| Flask-Login | Session authentication |
| Flask-WTF | CSRF protection & forms |
| Werkzeug | Password hashing |
| twilio | SMS API client |
| openpyxl | Excel export |
| reportlab | PDF export |
| python-dotenv | Environment variable loading |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## 📄 License

MIT License — free for academic and commercial use.
