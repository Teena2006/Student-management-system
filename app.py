from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB = "database/database.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs("database", exist_ok=True)
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        department TEXT NOT NULL,
        year INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        attendance_date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present','Absent')),
        FOREIGN KEY(student_id) REFERENCES students(id)
    );
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        due_date TEXT,
        status TEXT NOT NULL DEFAULT 'Pending'
    );
    """)
    conn.commit()
    conn.close()

@app.route("/")
def index():
    conn = get_db()
    students = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    present = conn.execute("SELECT COUNT(*) FROM attendance WHERE status='Present'").fetchone()[0]
    total_att = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
    attendance_rate = round((present / total_att) * 100, 1) if total_att else 0
    pending_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Pending'").fetchone()[0]
    conn.close()
    return render_template("index.html", students=students, total_students=total_students,
                           attendance_rate=attendance_rate, pending_tasks=pending_tasks)

@app.route("/students", methods=["GET", "POST"])
def students():
    conn = get_db()
    if request.method == "POST":
        try:
            conn.execute(
                "INSERT INTO students (name,email,department,year) VALUES (?,?,?,?)",
                (request.form["name"], request.form["email"], request.form["department"], request.form["year"])
            )
            conn.commit()
            flash("Student added successfully.", "success")
        except sqlite3.IntegrityError:
            flash("Email already exists.", "danger")
        finally:
            conn.close()
        return redirect(url_for("students"))
    rows = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("students.html", students=rows)

@app.route("/students/delete/<int:student_id>")
def delete_student(student_id):
    conn = get_db()
    conn.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
    conn.execute("DELETE FROM students WHERE id=?", (student_id,))
    conn.commit()
    conn.close()
    flash("Student deleted.", "success")
    return redirect(url_for("students"))

@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    conn = get_db()
    if request.method == "POST":
        conn.execute(
            "INSERT INTO attendance (student_id, attendance_date, status) VALUES (?,?,?)",
            (request.form["student_id"], request.form["attendance_date"], request.form["status"])
        )
        conn.commit()
        flash("Attendance saved.", "success")
        conn.close()
        return redirect(url_for("attendance"))
    students = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    records = conn.execute("""
        SELECT attendance.id, students.name, attendance.attendance_date, attendance.status
        FROM attendance JOIN students ON students.id = attendance.student_id
        ORDER BY attendance.id DESC LIMIT 30
    """).fetchall()
    conn.close()
    return render_template("attendance.html", students=students, records=records, today=date.today().isoformat())

@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    conn = get_db()
    if request.method == "POST":
        conn.execute(
            "INSERT INTO tasks (title,description,due_date) VALUES (?,?,?)",
            (request.form["title"], request.form["description"], request.form["due_date"])
        )
        conn.commit()
        flash("Task added.", "success")
        conn.close()
        return redirect(url_for("tasks"))
    rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("tasks.html", tasks=rows)

@app.route("/tasks/toggle/<int:task_id>")
def toggle_task(task_id):
    conn = get_db()
    task = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
    if task:
        new_status = "Completed" if task["status"] == "Pending" else "Pending"
        conn.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, task_id))
        conn.commit()
    conn.close()
    return redirect(url_for("tasks"))

@app.route("/tasks/delete/<int:task_id>")
def delete_task(task_id):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    flash("Task deleted.", "success")
    return redirect(url_for("tasks"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
