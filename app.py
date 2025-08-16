from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length
from passlib.hash import pbkdf2_sha256
import os
from datetime import datetime
import requests
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# --- Use Gramformer for grammar correction ---
from gramformer import Gramformer

gf = Gramformer(models=1)  # 1 means grammar correction only

def correct_grammar(text):
    corrected = list(gf.correct(text))
    # Gramformer returns a set of corrected sentences, pick the first (best) one
    return corrected[0] if corrected else text

# Initialize Flask app
load_dotenv()
app = Flask(__name__)
print(os.getenv('SECRET_KEY'))
app.secret_key = os.getenv('SECRET_KEY') or os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
app.config['HF_API_KEY'] = os.getenv('HF_API_KEY')
app.config['WHISPER_MODEL'] = 'openai/whisper-medium'

db = SQLAlchemy(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Models
class User(db.Model):
    __tablename__ = 'users'
    userName = db.Column(db.String(80), primary_key=True, nullable=False)
    course = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    year = db.Column(db.String(10), nullable=True)
    admission_number = db.Column(db.String(50), unique=True, nullable=True)
    role = db.Column(db.String(20), nullable=False)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)

class Lecture(db.Model):
    __tablename__ = 'lectures'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    course = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(80), nullable=False)

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(80), db.ForeignKey('users.userName'))
    course_code = db.Column(db.String(120), nullable=False)

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
    
    enrolled_courses = [e.course_code for e in Enrollment.query.filter_by(
        student_id=session['user']['username']).all()]
    
    lectures = Lecture.query.filter(
        (Lecture.course.in_(enrolled_courses)) |
        ((Lecture.course == session['user']['course']) & 
         (Lecture.year == session['user']['year']))
    ).order_by(Lecture.timestamp.desc()).all()
    
    return render_template("student_dashboard.html", 
                         lectures=lectures,
                         user=session['user'])

@app.route("/logout")
def logout():
    if 'user' not in session:
        flash('You were not logged in', 'info')
    else:
        session.pop('user', None)
        flash('You have been logged out', 'success')
    return redirect(url_for('main'))
    
@app.route('/lectures/<int:lecture_id>')
def view_lecture(lecture_id):
    if 'user' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('main'))
    
    lecture = Lecture.query.get_or_404(lecture_id)
    user = session['user']
    
    if user['role'] == 'student':
        enrolled = Enrollment.query.filter_by(
            student_id=user['username'],
            course_code=lecture.course
        ).first()
        
        if not enrolled and (lecture.course != user['course'] or 
                           lecture.year != user['year']):
            flash('You do not have access to this lecture', 'error')
            return redirect(url_for('student_dashboard'))
    
    return render_template('lecture_detail.html', lecture=lecture)

# New API endpoints for Whisper integration
@app.route('/api/start_recording', methods=['POST'])
def start_recording():
    if 'user' not in session or session['user']['role'] != 'lecturer':
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'status': 'ready'})

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    if 'user' not in session or session['user']['role'] != 'lecturer':
        return jsonify({'error': 'Unauthorized'}), 401
        
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
        
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    try:
        filename = secure_filename(audio_file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(temp_path)
        
        with open(temp_path, 'rb') as f:
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{app.config['WHISPER_MODEL']}",
                headers={"Authorization": f"Bearer {app.config['HF_API_KEY']}"},
                data=f.read()
            )
        
        os.remove(temp_path)
        
        if response.status_code != 200:
            return jsonify({'error': 'Transcription failed', 'details': response.text}), 500
            
        result = response.json()
        return jsonify({'text': result.get('text', '')})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save_lecture', methods=['POST'])
def save_lecture():
    if 'user' not in session or session['user']['role'] != 'lecturer':
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    if not data or not all(k in data for k in ['title', 'course', 'year', 'content']):
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        # Correct grammar in title and content!
        corrected_title = correct_grammar(data['title'])
        corrected_content = correct_grammar(data['content'])
        
        new_lecture = Lecture(
            title=corrected_title,
            course=data['course'],
            year=data['year'],
            content=corrected_content,
            author=session['user']['username']
        )
        db.session.add(new_lecture)
        db.session.commit()
        return jsonify({'success': True, 'lecture_id': new_lecture.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route("/testing")
def aroo():
    return render_template("transcriber.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
