from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length
from passlib.hash import pbkdf2_sha256
import os
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Forms
class SignInForm(FlaskForm):
    userName = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    role = SelectField("Role", choices=[
        ('admin', 'Admin'),
        ('lecturer', 'Lecturer'),
        ('student', 'Student')
    ], validators=[DataRequired()])
    submit = SubmitField("Login")

class AddUserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=4)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    admission_number = StringField("Admission Number", validators=[DataRequired()])
    course = StringField("Course", validators=[DataRequired()])
    year = SelectField("Year", choices=[
        ('1', 'First Year'),
        ('2', 'Second Year'),
        ('3', 'Third Year'),
        ('4', 'Fourth Year')
    ], validators=[DataRequired()])
    role = SelectField("Role", choices=[
        ('admin', 'Admin'),
        ('lecturer', 'Lecturer'),
        ('student', 'Student')
    ], validators=[DataRequired()])
    submit = SubmitField("Add User")

class LectureForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    course = StringField("Course", validators=[DataRequired()])
    year = SelectField("Year", choices=[
        ('1', 'First Year'),
        ('2', 'Second Year'),
        ('3', 'Third Year'),
        ('4', 'Fourth Year')
    ], validators=[DataRequired()])
    submit = SubmitField("Save Lecture")

# Models
class User(db.Model):
    __tablename__ = 'users'
    userName = db.Column(db.String(80), primary_key=True, nullable=False)
    course = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    year = db.Column(db.String(10), nullable=True)
    admission_number = db.Column(db.String(50), unique=True, nullable=True)
    role = db.Column(db.String(20), nullable=False)

class Lecture(db.Model):
    __tablename__ = 'lectures'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    course = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(80), nullable=False)

# Routes
@app.route("/", methods=["GET", "POST"])
def main():
    form = SignInForm()
    if form.validate_on_submit():
        user = User.query.filter_by(userName=form.userName.data).first()
        
        if not user:
            flash("Username not found!", "error")
        elif not pbkdf2_sha256.verify(form.password.data, user.password):
            flash("Wrong password!", "error")
        elif user.role.lower() != form.role.data.lower():
            flash("Role mismatch!", "error")
        else:
            session['user'] = {
                'username': user.userName,
                'role': user.role.lower(),
                'course': user.course,
                'year': user.year
            }
            
            if user.role.lower() == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role.lower() == 'lecturer':
                return redirect(url_for('lecturer_dashboard'))
            elif user.role.lower() == 'student':
                return redirect(url_for('student_dashboard'))

    return render_template("login.html", form=form)

@app.route("/admin")
def admin_dashboard():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('main'))
    
    form = AddUserForm()
    users = User.query.all()
    return render_template("admin_dashboard.html", form=form, users=users)

@app.route("/admin/add_user", methods=["POST"])
def add_user():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('main'))
    
    form = AddUserForm()
    if form.validate_on_submit():
        if User.query.filter_by(userName=form.username.data).first():
            flash("Username already exists!", "error")
        else:
            new_user = User(
                userName=form.username.data,
                password=pbkdf2_sha256.hash(form.password.data),
                admission_number=form.admission_number.data,
                course=form.course.data,
                year=form.year.data,
                role=form.role.data
            )
            db.session.add(new_user)
            db.session.commit()
            flash("User created successfully!", "success")
    
    return redirect(url_for('admin_dashboard'))

@app.route("/lecturer")
def lecturer_dashboard():
    if 'user' not in session or session['user']['role'] != 'lecturer':
        return redirect(url_for('main'))
    
    lectures = Lecture.query.filter_by(author=session['user']['username'])\
                  .order_by(Lecture.timestamp.desc()).all()
    return render_template("lecturer_dashboard.html", lectures=lectures)

@app.route("/student")
def student_dashboard():
    if 'user' not in session or session['user']['role'] != 'student':
        return redirect(url_for('main'))
    
    lectures = Lecture.query.filter_by(
        course=session['user']['course'],
        year=session['user']['year']
    ).order_by(Lecture.timestamp.desc()).all()
    
    # Pass the user data from session to template
    return render_template("student_dashboard.html", 
                         lectures=lectures,
                         user=session['user'])
@app.route("/start_recording", methods=["POST"])
def start_recording():
    if 'user' not in session or session['user']['role'] != 'lecturer':
        return jsonify({"error": "Unauthorized"}), 401
    session['recording'] = True
    session['transcript'] = ""
    return jsonify({"status": "Recording started"})

@app.route("/save_lecture", methods=["POST"])
def save_lecture():
    if 'user' not in session or session['user']['role'] != 'lecturer':
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    new_lecture = Lecture(
        title=data['title'],
        course=data['course'],
        year=data['year'],
        content=data['content'],
        author=session['user']['username']
    )
    
    db.session.add(new_lecture)
    db.session.commit()
    
    return jsonify({"status": "Lecture saved successfully"})

@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for('main'))
@app.route("/get_lectures")
def get_lectures():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user = User.query.filter_by(userName=session['user']['username']).first()
    
    if session['user']['role'] == 'student':
        lectures = Lecture.query.filter_by(
            course=user.course,
            year=user.year
        ).order_by(Lecture.timestamp.desc()).all()
    else:
        lectures = Lecture.query.order_by(Lecture.timestamp.desc()).all()
    
    lectures_data = [{
        'id': lecture.id,
        'title': lecture.title,
        'course': lecture.course,
        'year': lecture.year,
        'content': lecture.content,
        'author': lecture.author,
        'timestamp': lecture.timestamp.strftime('%Y-%m-%d %H:%M')
    } for lecture in lectures]
    
    return jsonify(lectures_data)
@app.route('/lectures/<int:lecture_id>')
def view_lecture(lecture_id):
    # Verify student has access to this lecture
    lecture = Lecture.query.get_or_404(lecture_id)
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=lecture.course_id
    ).first()
    
    if not enrollment and current_user.role != 'admin':
        flash('You do not have access to this lecture', 'error')
        return redirect(url_for('student_dashboard'))
    
    return render_template('view_lecture.html', lecture=lecture)
@app.route("/get_lecture/<int:lecture_id>")
def get_lecture(lecture_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    lecture = Lecture.query.get_or_404(lecture_id)
    return jsonify({
        'id': lecture.id,
        'title': lecture.title,
        'course': lecture.course,
        'year': lecture.year,
        'content': lecture.content,
        'author': lecture.author,
        'timestamp': lecture.timestamp.strftime('%Y-%m-%d %H:%M')
    })
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)