from re import S
from tkinter import X
from flask import render_template, flash, redirect, url_for, request, session
from flask_login import login_user, current_user, login_required, logout_user
from sqlalchemy import func
import operator
import os

from app import app, bcrypt, db
from app.forms import *
from app.models import User, RegisterCourse 

from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           

@app.route('/', methods = ['GET', 'POST'])
def home():
    return render_template('home.html', title='Home')

@app.route('/about')
def about():
    return render_template('about.html', title='About')

@app.route('/register', methods = ['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
       username = form.username.data
       email = form.email.data
       password = bcrypt.generate_password_hash(form.password.data)
       user=User(username=username, email=email, password=password)
       db.session.add(user)
       db.session.commit()
       flash('Registration Sucess', category='success')
       return redirect(url_for('login'))
       
    return render_template('register.html', title='Registration', form=form)

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('User already login', category='info')
        return redirect(url_for('account'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember.data
        #password check
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember = remember)
            flash('Login success', category='info')
            
            if request.args.get('next'):
                next_page = request.args.get('next')
                return redirect(next_page)
            return redirect(url_for('session_cart'))
        
        flash('User not exist or password unmatch', category='danger')
        
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/course', methods=['GET','POST'])
def course():
    cart = session.get('cart', {'cake':0, 'cookie':0, 'bread and bun':0, 'brownie':0, 'mooncake':0})
    
    #Course ranking
    CakeNum = RegisterCourse.query.filter_by(course='cake').with_entities(func.sum(RegisterCourse.quantity).label('cakes')).first().cakes
    CookieNum = RegisterCourse.query.filter_by(course='cookie').with_entities(func.sum(RegisterCourse.quantity).label('cookies')).first().cookies
    BunNum = RegisterCourse.query.filter_by(course='bread and bun').with_entities(func.sum(RegisterCourse.quantity).label('buns')).first().buns
    BrownieNum = RegisterCourse.query.filter_by(course='brownie').with_entities(func.sum(RegisterCourse.quantity).label('brownies')).first().brownies
    MooncakeNum = RegisterCourse.query.filter_by(course='mooncake').with_entities(func.sum(RegisterCourse.quantity).label('mooncakes')).first().mooncakes
    
    if CakeNum:
        pass
    else:
        CakeNum=0
    if CookieNum:
        pass
    else:
        CookieNum=0    
    if BunNum:
        pass
    else:
        BunNum=0
    if BrownieNum:
        pass
    else:
        BrownieNum=0
    if MooncakeNum:
        pass
    else:
        MooncakeNum=0
    
    Courses = {'cake':CakeNum, 'cookie':CookieNum, 'bread and bun':BunNum, 'brownie':BrownieNum, 'mooncake':MooncakeNum}
    
    #Ranking sort
    CourseRank = dict(sorted(Courses.items(), key=operator.itemgetter(1),reverse=True))
    #double sort in template
   
   
    if request.method == 'POST':
        # add to cart
        courses = request.form.get('coursesid')
        if cart[courses] ==1:
            flash('You can only register each course per account', category='info' )
        
        else:
            if Courses[courses] >= 5:
                    flash('Course capacity have already full', category='info' )
            else:
                    cart[courses] += 1
                    flash('You have added '+ courses, category='info' )
                    session['cart'] = cart
                    return redirect(url_for('session_cart'))
            

    return render_template('course.html', title='Course', cart=cart, CourseRank=CourseRank)  

@app.route('/cart', methods=['GET','POST'])
def session_cart():
    if 'cart' in session:
        cart = session.get('cart')
        show = session.get('show_cart', True)
    else:
        session['cart'] = {'cake':0, 'cookie':0, 'bread and bun':0, 'brownie':0, 'mooncake':0}
        return redirect(request.referrer)
    
    return render_template('cart.html', title='Cart', cartContents=show, cart=cart)

@app.route('/clearCart', methods=['POST'])
def clearCart():
    session['cart'] = {'cake':0, 'cookie':0, 'bread and bun':0, 'brownie':0, 'mooncake':0}
    flash('Cart cleared', category='info')
    return redirect(url_for('session_cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    if session['cart'] == {'cake':0, 'cookie':0, 'bread and bun':0, 'brownie':0, 'mooncake':0}:
        flash('You must add course before checkout', category='info')
        return redirect(url_for('course'))
    
    if current_user.is_authenticated:
        username=current_user.username
        user = User.query.filter_by(username=username).first()
        registerCourse = RegisterCourse.query.filter_by(user_id=user.id).all()
        registerCourses = list(dict.fromkeys(registerCourse))
        
        session['carts'] = session['cart']
        for key, value in session['carts'].items():
            for registerCourse in registerCourses:
                if key in registerCourse.course:
                    if value == registerCourse.quantity:
                        flash('You can only register each course per account', category='info' )
                        return redirect(url_for('session_cart')) 
                    
    if current_user.is_authenticated:
        return redirect(url_for('payment'))
    else:
        flash('You must login before checkout', category='info')
        return redirect(url_for('session_cart'))
      
    
@app.route('/payment', methods=['GET','POST'])
@login_required
def payment():
    if 'cart' in session:
        cart = session.get('cart')
        show = session.get('show_cart', True)
    else:
        return redirect(url_for('session_cart'))
    
    prices = {'cake':85, 'cookie':115, 'bread and bun':145, 'brownie':105, 'mooncake':125}
    x=session['cart']
                   
    if session['cart'] == {'cake':0, 'cookie':0, 'bread and bun':0, 'brownie':0, 'mooncake':0}:
        flash('You must add course before checkout', category='info')
        return redirect(url_for('session_cart'))
    
    form = upload_payment()
    if current_user.is_authenticated:
        
      if form.validate_on_submit():
        f = form.receipt.data
    
        if f.filename == '':
            flash('No selected file', category = 'danger')
            return render_template(url_for('payment'), form=form)
        
        if f and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            f.save(os.path.join('app', 'static', 'assets', filename))
            
            #add to user database
            for key, value in session['cart'].items():
              if value>=1:
                registerCourse = RegisterCourse(course=key,quantity=value)
                current_user.registerCourses.append(registerCourse)
                db.session.commit()
            
            flash(' You have successfully register', category='success')
            session['cart'] = {'cake':0, 'cookie':0, 'bread and bun':0, 'brownie':0, 'mooncake':0}
            session.pop("carts", None)

            return redirect(url_for('account', username= current_user.username))
        
      return render_template('payment.html', form=form, cartContents=show, cart=cart, prices=prices,x=x)
  
    else:
        flash('You must login before checkout', category='info')
        return redirect(url_for('login'))

@app.route('/account')
@login_required
def account():
    username=current_user.username
    user = User.query.filter_by(username=username).first()
    if user:
        page = request.args.get('page',1,type=int)
        registerCourses = RegisterCourse.query.filter_by(user_id=user.id).order_by(RegisterCourse.date_registered.desc()).paginate(page,10,False)
        
        return render_template('account.html', title='Account', registerCourses=registerCourses, user=user)
    else:
        return '404'
    
@app.route('/User_course/<username>')
@login_required
def user_course(username):
    CakeMate = RegisterCourse.query.filter_by(course='cake').all()
    CookieMate = RegisterCourse.query.filter_by(course='cookie').all()
    BunMate = RegisterCourse.query.filter_by(course='bread and bun').all()
    BrownieMate = RegisterCourse.query.filter_by(course='brownie').all()
    MooncakeMate = RegisterCourse.query.filter_by(course='mooncake').all()
    
    CourseMates= {'cake':CakeMate, 'cookie':CookieMate, 'bread and bun':BunMate, 'brownie':BrownieMate, 'mooncake':MooncakeMate}
    
    username=current_user.username
    user = User.query.filter_by(username=username).first()
    registerCourses = RegisterCourse.query.filter_by(user_id=user.id).all()
    
    return render_template('user_course.html', title='Your schedule', user=username, CourseMates=CourseMates, registerCourses=registerCourses )
