import os
import operator
from re import S
from flask import render_template, flash, redirect, url_for, request, session, make_response
from flask_login import login_user, current_user, login_required, logout_user
from sqlalchemy import func
from decimal import Decimal
from rdflib import Graph
from SPARQLWrapper import SPARQLWrapper, JSON
from datetime import datetime

from app import app, bcrypt, db
from app.forms import *
from app.models import User, RegisterCourse, Admin 

from werkzeug.utils import secure_filename

import xml.etree.ElementTree as ET

ALLOWED_EXTENSIONS = {'ttl'}

def verify_receipt(content, cart, prices, username):
    try:
        g = Graph()
        g.parse(data=content, format='turtle')
        
        sparql = SPARQLWrapper("sparql")
        sparql.setReturnFormat(JSON)
        
        query_check_date = """
        PREFIX pb: <http://peoplebakery.com/ns#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?date
        WHERE {
            ?receipt a pb:Receipt ;
                     pb:date ?date .
        }
        """
        
        results = g.query(query_check_date)
        receipt_date = None
        for result in results:
            receipt_date = str(result[0]).split('T')[0]
            
        today = datetime.now().strftime('%Y-%m-%d')
        if receipt_date != today:
            return False, "Receipt date must be today's date"
            
        query_check_user = """
        PREFIX pb: <http://peoplebakery.com/ns#>
        SELECT ?username
        WHERE {
            ?receipt a pb:Receipt ;
                     pb:issuedTo ?user .
            ?user pb:username ?username .
        }
        """
        
        results = g.query(query_check_user)
        receipt_username = None
        for result in results:
            receipt_username = str(result[0])
            
        if receipt_username != username:
            return False, "Receipt username does not match current user"
            
        query_check_course_price = """
        PREFIX pb: <http://peoplebakery.com/ns#>
        SELECT ?courseName ?coursePrice
        WHERE {
            ?receipt a pb:Receipt ;
                     pb:includesCourse ?course .
            ?course pb:courseName ?courseName ;
                    pb:price ?coursePrice .
        }
        """
        
        receipt_courses = set()
        sparql.setQuery(query_check_course_price)
        for result in g.query(query_check_course_price):
            course_name = str(result[0]).lower()
            course_price = float(result[1])
            receipt_courses.add(course_name)
            
            if course_name in cart and cart[course_name] > 0:
                expected_price = float(prices[course_name])
                if abs(course_price - expected_price) > 0.01:
                    return False, f"Course price mismatch for {course_name}: Receipt shows ${course_price}"

        cart_courses = {course.lower() for course, qty in cart.items() if qty > 0}
        if cart_courses != receipt_courses:
            return False, "Courses in receipt do not match cart contents"

        query_check_total_price = """
        PREFIX pb: <http://peoplebakery.com/ns#>
        SELECT ?totalPrice ?regFee
        WHERE {
            ?receipt a pb:Receipt ;
                     pb:totalPrice ?totalPrice ;
                     pb:registrationFee ?regFee .
        }
        """
        
        reg_fee = 20.00
        course_total = sum(prices[course] * qty for course, qty in cart.items() if qty > 0)
        expected_total = reg_fee + course_total
        
        results = g.query(query_check_total_price)
        for result in results:
            receipt_total = float(result[0])
            receipt_reg_fee = float(result[1])
            
            if receipt_reg_fee != reg_fee:
                return False, f"Registration fee ${receipt_reg_fee} does not match required fee ${reg_fee}"
                
            if abs(receipt_total - expected_total) > 0.01:
                return False, f"Receipt total ${receipt_total} does not match expected total ${expected_total}"
            
        return True, "Receipt validation successful"
        
    except Exception as e:
        return False, f"Error parsing receipt: {str(e)}"

def is_valid_ttl(content):
    content_str = content.decode('utf-8')
    required_elements = [
        '@prefix', 'pb:Receipt', 'pb:issuedTo', 'pb:includesCourse',
        'pb:totalPrice', 'pb:registrationFee', 'pb:date'
    ]
    return all(element in content_str for element in required_elements)

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

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and bcrypt.check_password_hash(admin.password, form.password.data):
            session['admin_logged_in'] = True
            session['admin_username'] = admin.username
            flash('Welcome Admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('admin_login.html', form=form)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('You must be logged in as admin to view this page.', 'warning')
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

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
            return render_template('payment.html', form=form, cartContents=show, cart=cart, prices=prices, x=x)
        
        if f and allowed_file(f.filename):
            content = f.read()
            if not is_valid_ttl(content):
                flash('Invalid TTL file format. Please provide a valid RDF receipt file.', category='danger')
                return render_template('payment.html', form=form, cartContents=show, cart=cart, prices=prices, x=x)
            
            is_valid, error_message = verify_receipt(content, cart, prices, current_user.username)
            if not is_valid:
                flash(f'Invalid receipt: {error_message}', category='danger')
                return render_template('payment.html', form=form, cartContents=show, cart=cart, prices=prices, x=x)
            
            f.seek(0)
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
        registerCourses = RegisterCourse.query.filter_by(user_id=user.id).order_by(RegisterCourse.date_registered.desc()).paginate()
        
        return render_template('account.html', title='Account', registerCourses=registerCourses, user=user)
    else:
        return '404'
    
@app.route('/export/calendar/<username>')
@login_required
def export_calendar(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        flash("User not found", category='danger')
        return redirect(url_for('account'))

    registerCourses = RegisterCourse.query.filter_by(user_id=user.id).all()

    # Mapping of course to day
    course_schedule = {
        "cake": "Saturday",
        "cookie": "Friday",
        "bread and bun": "Thursday",
        "brownie": "Wednesday",
        "mooncake": "Tuesday"
    }

    root = ET.Element("Schedule")
    for course in registerCourses:
        course_elem = ET.SubElement(root, "Course")
        course_name = course.course.lower()

        ET.SubElement(course_elem, "Name").text = course.course.title()
        ET.SubElement(course_elem, "Date").text = course.date_registered.strftime('%Y-%m-%d')
        ET.SubElement(course_elem, "Day").text = course_schedule.get(course_name, "Unassigned")
        ET.SubElement(course_elem, "Time").text = "8:00 PM - 10:00 PM"
        ET.SubElement(course_elem, "Duration").text = "10 hours"
        ET.SubElement(course_elem, "Modules").text = "5"

    xml_data = ET.tostring(root, encoding='utf-8', method='xml')

    response = make_response(xml_data)
    response.headers['Content-Type'] = 'application/xml'
    response.headers['Content-Disposition'] = f'attachment; filename={username}_calendar.xml'
    return response
    
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

@app.route('/admin/export')
def export_students_by_course():
    if 'admin_username' not in session:
        flash('Access denied. Please log in as admin.', 'danger')
        return redirect(url_for('admin_login'))

    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom.minidom import parseString

    root = Element('Courses')

    courses = db.session.query(RegisterCourse.course).distinct()
    for course_entry in courses:
        course_name = course_entry.course
        course_elem = SubElement(root, 'Course', name=course_name)

        students = RegisterCourse.query.filter_by(course=course_name).all()
        for student in students:
            student_elem = SubElement(course_elem, 'Student')
            SubElement(student_elem, 'Username').text = student.person.username
            SubElement(student_elem, 'Email').text = student.person.email
            SubElement(student_elem, 'Quantity').text = str(student.quantity)
            SubElement(student_elem, 'DateRegistered').text = student.date_registered.strftime('%Y-%m-%d')

    xml_str = parseString(tostring(root)).toprettyxml(indent="  ")
    response = make_response(xml_str)
    response.headers['Content-Type'] = 'application/xml'
    response.headers['Content-Disposition'] = 'attachment; filename=students_by_course.xml'
    return response