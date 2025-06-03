from flask_login import UserMixin
from app import db, login
from datetime import datetime

@login.user_loader
def load_user(user_id):
    return User.query.filter_by(id=user_id).first()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    
    registerCourses = db.relationship('RegisterCourse', backref=db.backref('person', lazy=True ))

    def __repr__(self):
        return f'{self.username}'

class RegisterCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course = db.Column(db.String, nullable=False)
    quantity = db.Column(db.Integer,nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'{self.person}'

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    
    def __repr__(self):
        return f'<Admin {self.username}>'

