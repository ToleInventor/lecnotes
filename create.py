from app import app, db, User
from passlib.hash import pbkdf2_sha256

def create_admin():
    with app.app_context():
        username = input("Enter admin username: ")
        password = input("Enter admin password: ")
        
        if User.query.filter_by(userName=username).first():
            print("Error: User already exists!")
            return
        
        hashed_pw = pbkdf2_sha256.hash(password)
        admin = User(
            userName=username,
            course="Administration",
            password=hashed_pw,
            admission_number="ADMIN001",
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin '{username}' created successfully!")

if __name__ == "__main__":
    create_admin()