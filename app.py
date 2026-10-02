from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "student_attendance_secret_key"

DATABASE = "attendance.db"


# ---------------- DATABASE CONNECTION ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------- CREATE DATABASE ----------------

def create_database():

    conn = get_db()

    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Students table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            roll_number TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            FOREIGN KEY(user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
        )
    """)

    # Attendance table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            UNIQUE(student_id, date),
            FOREIGN KEY(student_id)
            REFERENCES students(id)
            ON DELETE CASCADE
        )
    """)

    # Create default admin
    admin = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        ("admin",)
    ).fetchone()

    if admin is None:

        admin_password = generate_password_hash("admin123")

        conn.execute("""
            INSERT INTO users
            (username, password, role)
            VALUES (?, ?, ?)
        """, ("admin", admin_password, "admin"))

    conn.commit()
    conn.close()


# ---------------- LOGIN ----------------

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin_dashboard")

            else:
                return redirect("/student_dashboard")

        flash("Invalid username or password")

    return render_template("login.html")


# ---------------- STUDENT REGISTRATION ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        roll_number = request.form["roll_number"]
        department = request.form["department"]
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:

            flash("Passwords do not match")
            return redirect("/register")

        conn = get_db()

        try:

            hashed_password = generate_password_hash(password)

            cursor = conn.execute("""
                INSERT INTO users
                (username, password, role)
                VALUES (?, ?, 'student')
            """, (
                username,
                hashed_password
            ))

            user_id = cursor.lastrowid

            conn.execute("""
                INSERT INTO students
                (user_id, name, roll_number, department)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                name,
                roll_number,
                department
            ))

            conn.commit()

            flash("Registration successful. Please login.")

            conn.close()

            return redirect("/")

        except sqlite3.IntegrityError:

            conn.rollback()
            conn.close()

            flash("Username or Roll Number already exists")

            return redirect("/register")

    return render_template("register.html")


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin_dashboard")
def admin_dashboard():

    if session.get("role") != "admin":
        return redirect("/")

    conn = get_db()

    total_students = conn.execute("""
        SELECT COUNT(*)
        FROM students
    """).fetchone()[0]

    total_present = conn.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE status = 'Present'
    """).fetchone()[0]

    total_absent = conn.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE status = 'Absent'
    """).fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        total_present=total_present,
        total_absent=total_absent
    )


# ---------------- STUDENT DASHBOARD ----------------

@app.route("/student_dashboard")
def student_dashboard():

    if session.get("role") != "student":
        return redirect("/")

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    present = 0
    absent = 0

    if student:

        present = conn.execute("""
            SELECT COUNT(*)
            FROM attendance
            WHERE student_id = ?
            AND status = 'Present'
        """, (
            student["id"],
        )).fetchone()[0]

        absent = conn.execute("""
            SELECT COUNT(*)
            FROM attendance
            WHERE student_id = ?
            AND status = 'Absent'
        """, (
            student["id"],
        )).fetchone()[0]

    conn.close()

    return render_template(
        "student_dashboard.html",
        student=student,
        present=present,
        absent=absent
    )


# ---------------- VIEW STUDENTS ----------------

@app.route("/students")
def students():

    if session.get("role") != "admin":
        return redirect("/")

    conn = get_db()

    students = conn.execute("""
        SELECT
            students.*,
            users.username
        FROM students
        LEFT JOIN users
        ON students.user_id = users.id
        ORDER BY students.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "students.html",
        students=students
    )


# ---------------- ADD STUDENT ----------------

@app.route("/add_student", methods=["GET", "POST"])
def add_student():

    if session.get("role") != "admin":
        return redirect("/")

    if request.method == "POST":

        name = request.form["name"]
        roll_number = request.form["roll_number"]
        department = request.form["department"]
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        try:

            hashed_password = generate_password_hash(password)

            cursor = conn.execute("""
                INSERT INTO users
                (username, password, role)
                VALUES (?, ?, 'student')
            """, (
                username,
                hashed_password
            ))

            user_id = cursor.lastrowid

            conn.execute("""
                INSERT INTO students
                (user_id, name, roll_number, department)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                name,
                roll_number,
                department
            ))

            conn.commit()

            flash("Student added successfully")

        except sqlite3.IntegrityError:

            conn.rollback()

            flash("Username or Roll Number already exists")

        conn.close()

        return redirect("/students")

    return render_template("add_student.html")


# ---------------- EDIT STUDENT ----------------

@app.route("/edit_student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):

    if session.get("role") != "admin":
        return redirect("/")

    conn = get_db()

    student = conn.execute("""
        SELECT
            students.*,
            users.username
        FROM students
        LEFT JOIN users
        ON students.user_id = users.id
        WHERE students.id = ?
    """, (
        student_id,
    )).fetchone()

    if student is None:

        conn.close()
        return redirect("/students")

    if request.method == "POST":

        name = request.form["name"]
        roll_number = request.form["roll_number"]
        department = request.form["department"]
        username = request.form["username"]
        password = request.form["password"]

        try:

            conn.execute("""
                UPDATE students
                SET
                    name = ?,
                    roll_number = ?,
                    department = ?
                WHERE id = ?
            """, (
                name,
                roll_number,
                department,
                student_id
            ))

            conn.execute("""
                UPDATE users
                SET username = ?
                WHERE id = ?
            """, (
                username,
                student["user_id"]
            ))

            if password:

                hashed_password = generate_password_hash(password)

                conn.execute("""
                    UPDATE users
                    SET password = ?
                    WHERE id = ?
                """, (
                    hashed_password,
                    student["user_id"]
                ))

            conn.commit()

            flash("Student updated successfully")

        except sqlite3.IntegrityError:

            conn.rollback()

            flash("Username or Roll Number already exists")

        conn.close()

        return redirect("/students")

    conn.close()

    return render_template(
        "edit_student.html",
        student=student
    )


# ---------------- DELETE STUDENT ----------------

@app.route("/delete_student/<int:student_id>", methods=["POST"])
def delete_student(student_id):

    if session.get("role") != "admin":
        return redirect("/")

    conn = get_db()

    student = conn.execute("""
        SELECT user_id
        FROM students
        WHERE id = ?
    """, (
        student_id,
    )).fetchone()

    if student:

        conn.execute("""
            DELETE FROM students
            WHERE id = ?
        """, (
            student_id,
        ))

        conn.execute("""
            DELETE FROM users
            WHERE id = ?
        """, (
            student["user_id"],
        ))

        conn.commit()

    conn.close()

    return redirect("/students")


# ---------------- ATTENDANCE ----------------

@app.route("/attendance", methods=["GET", "POST"])
def attendance():

    if session.get("role") != "admin":
        return redirect("/")

    conn = get_db()

    students = conn.execute("""
        SELECT *
        FROM students
        ORDER BY roll_number
    """).fetchall()

    if request.method == "POST":

        date = request.form["date"]

        for student in students:

            status = request.form.get(
                f"status_{student['id']}"
            )

            if status:

                conn.execute("""
                    INSERT INTO attendance
                    (student_id, date, status)
                    VALUES (?, ?, ?)

                    ON CONFLICT(student_id, date)
                    DO UPDATE SET
                    status = excluded.status
                """, (
                    student["id"],
                    date,
                    status
                ))

        conn.commit()

        flash("Attendance saved successfully")

    # Attendance records for admin
    records = conn.execute("""
        SELECT
            attendance.id,
            attendance.date,
            attendance.status,
            students.name,
            students.roll_number
        FROM attendance
        JOIN students
        ON attendance.student_id = students.id
        ORDER BY attendance.date DESC
    """).fetchall()

    conn.close()

    return render_template(
        "attendance.html",
        students=students,
        records=records
    )


# ---------------- STUDENT ATTENDANCE ----------------

@app.route("/my_attendance")
def my_attendance():

    if session.get("role") != "student":
        return redirect("/")

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM students
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    records = []

    if student:

        records = conn.execute("""
            SELECT
                date,
                status
            FROM attendance
            WHERE student_id = ?
            ORDER BY date DESC
        """, (
            student["id"],
        )).fetchall()

    conn.close()

    return render_template(
        "student_attendance.html",
        student=student,
        records=records
    )


# ---------------- DELETE ATTENDANCE ----------------

@app.route("/delete_attendance/<int:attendance_id>", methods=["POST"])
def delete_attendance(attendance_id):

    if session.get("role") != "admin":
        return redirect("/")

    conn = get_db()

    conn.execute("""
        DELETE FROM attendance
        WHERE id = ?
    """, (
        attendance_id,
    ))

    conn.commit()
    conn.close()

    return redirect("/attendance")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":

    create_database()

    app.run(debug=True)