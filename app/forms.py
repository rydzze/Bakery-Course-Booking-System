from flask_wtf import FlaskForm, RecaptchaField
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError

from app.models import User

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=6,max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8,max=20)])
    confirm = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    recaptcha = RecaptchaField()
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username = username.data).first()
        if user:
            raise ValidationError('Username already taken')
    
    def validate_email(self, email):
        user = User.query.filter_by(email = email.data).first()
        if user:
            raise ValidationError('Email already taken')
        
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=6,max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8,max=20)])
    remember = BooleanField('Remember me')
    submit = SubmitField('Sign in')
    
class upload_payment(FlaskForm):
    receipt = FileField(validators= [FileRequired()])
    submit = SubmitField('Uploads')