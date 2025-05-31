import os
import xml.etree.ElementTree as ET
from .app import app
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from flask import render_template, request, redirect, url_for, session, flash
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS

g = Graph()
g.parse(os.path.join(os.path.dirname(__file__), "data", "products.ttl"), format="turtle")
BK = Namespace("http://bakestore.com/ontology#")
ADMIN_PASSWORD = 'BakeStore'

def get_products(keyword=None):
    base_query = """
        SELECT ?product ?name ?price ?description ?image
        WHERE {
            ?product rdf:type bakestore:Product ;
                bakestore:name ?name ;
                bakestore:price ?price ;
                bakestore:description ?description ;
                bakestore:image ?image .
            %s
        }
    """
    
    if keyword and keyword.strip():
        search_term = keyword.lower()
        filter_statement = f"""
            FILTER (
                CONTAINS(LCASE(STR(?name)), "{search_term}") ||
                CONTAINS(LCASE(STR(?description)), "{search_term}")
            )
        """
        query = base_query % filter_statement
    else:
        query = base_query % ""

    results = g.query(query, initNs={'bakestore': BK})
    products = []
    for row in results:
        products.append({
            'id': str(row.product).split('#')[1],
            'name': str(row.name),
            'price': float(str(row.price)),
            'description': str(row.description),
            'image': str(row.image)
        })

    return products

@app.route('/')
def index():    
    if 'user_name' not in session:
        return redirect(url_for('enter_name'))
    
    keyword = request.args.get('search', '')
    if keyword:
        keyword = keyword.strip()
        products = get_products(keyword)
    else:
        products = get_products()

    return render_template('user/index.html', products=products, 
                           user_name=session['user_name'], keyword=keyword)

@app.route('/enter_name', methods=['GET', 'POST'])
def enter_name():
    if request.method == 'POST':
        session['user_name'] = request.form['name']
        
        return redirect(url_for('index'))
    
    return render_template('user/enter_name.html')

@app.route('/add_to_cart/<product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = {}
    
    products = get_products()
    product = next((p for p in products if p['id'] == product_id), None)
    
    if product_id in session['cart']:
        session['cart'][product_id] += 1
        msg = f"Added another {product['name']} to cart"
    else:
        session['cart'][product_id] = 1
        msg = f"Added {product['name']} to cart"
    
    session.modified = True
    flash(msg, 'success')
    return redirect(url_for('index'))

@app.route('/remove_from_cart/<product_id>')
def remove_from_cart(product_id):
    if 'cart' in session and product_id in session['cart']:
        del session['cart'][product_id]
        session.modified = True

    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    if 'cart' not in session:
        return render_template('user/cart.html', items=[], total=0)
    
    total = 0
    cart_items = []
    products = get_products()
    products_dict = {p['id']: p for p in products}
    
    for product_id, quantity in session['cart'].items():
        product = products_dict.get(product_id)
        if product:
            item_total = product['price'] * quantity
            total += item_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
    
    return render_template('user/cart.html', items=cart_items, total=total)

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'cart' not in session or not session['cart']:
        return redirect(url_for('index'))

    order = ET.Element('order')
    ET.SubElement(order, 'date').text = datetime.now().isoformat()
    customer = ET.SubElement(order, 'customer')
    ET.SubElement(customer, 'name').text = session.get('user_name', 'Unknown')
    ET.SubElement(customer, 'contact').text = request.form.get('contact_number', 'Not provided')
    ET.SubElement(customer, 'address').text = request.form.get('home_address', 'Not provided')
    
    items = ET.SubElement(order, 'items')
    total = 0
    products = get_products()
    products_dict = {p['id']: p for p in products}
    
    for product_id, quantity in session['cart'].items():
        product = products_dict.get(product_id)
        if product:
            item = ET.SubElement(items, 'item')
            ET.SubElement(item, 'product').text = product['name']
            ET.SubElement(item, 'quantity').text = str(quantity)
            ET.SubElement(item, 'price').text = str(product['price'])
            item_total = product['price'] * quantity
            ET.SubElement(item, 'total').text = str(item_total)
            total += item_total
    
    ET.SubElement(order, 'total').text = str(total)
    order_id = datetime.now().strftime('%Y%m%d%H%M%S')
    records_dir = os.path.join(os.path.dirname(__file__), "records")
    if not os.path.exists(records_dir):
        os.makedirs(records_dir)
    
    from xml.dom import minidom
    xml_str = minidom.parseString(ET.tostring(order)).toprettyxml(indent="    ")
    
    with open(os.path.join(records_dir, f'order_{order_id}.xml'), 'w', encoding='utf-8') as f:
        f.write(xml_str)    
        session_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'flask_session',
                                    session.sid if hasattr(session, 'sid') else '')
    session.clear()
    
    if os.path.exists(session_file):
        os.remove(session_file)    
    
    receipt = generate_receipt_data(order_id)
    return render_template('user/receipt.html', receipt=receipt)

def generate_receipt_data(order_id):
    xml_path = os.path.join(os.path.dirname(__file__), "records", f"order_{order_id}.xml")
    if not os.path.exists(xml_path):
        return None
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    order_items = []
    items_element = root.find('items')

    if items_element is not None:
        for item in items_element.findall('item'):
            order_items.append({
                'product': item.find('product').text,
                'quantity': int(item.find('quantity').text),
                'price': float(item.find('price').text),
                'total': float(item.find('total').text)
            })
            
    customer = root.find('customer')
    customer_name = customer.find('name').text if customer is not None and customer.find('name') is not None else 'Unknown'
    contact_number = customer.find('contact').text if customer is not None and customer.find('contact') is not None else 'Not provided'
    home_address = customer.find('address').text if customer is not None and customer.find('address') is not None else 'Not provided'

    return {
        'id': order_id,
        'date': datetime.fromisoformat(root.find('date').text),
        'customer_name': customer_name,
        'contact_number': contact_number,
        'home_address': home_address,
        'order_items': order_items,
        'total_amount': float(root.find('total').text)
    }

def save_products_to_ttl():
    new_g = Graph()
    new_g.bind('', BK)
    new_g.bind('rdf', RDF)
    new_g.bind('rdfs', RDFS)
    
    schema_triples = [
        (BK.Product, RDF.type, RDFS.Class),
        (BK.name, RDF.type, RDF.Property),
        (BK.price, RDF.type, RDF.Property),
        (BK.description, RDF.type, RDF.Property),
        (BK.image, RDF.type, RDF.Property)
    ]
    for triple in schema_triples:
        new_g.add(triple)
    
    for s, p, o in g.triples((None, RDF.type, BK.Product)):
        new_g.add((s, p, o))
        for p2, o2 in g.predicate_objects(s):
            new_g.add((s, p2, o2))
    
    new_g.serialize(os.path.join(os.path.dirname(__file__), "data", "products.ttl"), format="turtle")



#  ADMIN ROUTES  

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('login', next=request.url))
        
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/admin')
@admin_required
def products():
    products = get_products()
    return render_template('admin/products.html', products=products)

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            next_page = request.args.get('next')

            if next_page:
                return redirect(next_page)

            return redirect(url_for('products'))
        error = 'Invalid password'

    return render_template('admin/login.html', error=error)

@app.route('/admin/logout')
def logout():
    session.pop('admin_authenticated', None)
    return redirect(url_for('index'))

@app.route('/admin/product/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        
        image = request.files['image']
        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(os.path.dirname(__file__), 'static', 'images', filename))
        
        product_id = name.replace(' ', '')
        product_uri = BK[product_id]
        
        g.add((product_uri, RDF.type, BK.Product))
        g.add((product_uri, BK.name, Literal(name)))
        g.add((product_uri, BK.price, Literal(price)))
        g.add((product_uri, BK.description, Literal(description)))
        g.add((product_uri, BK.image, Literal(filename)))
        
        save_products_to_ttl()

        return redirect(url_for('products'))
        
    return render_template('admin/product_form.html', product=None)

@app.route('/admin/product/edit/<product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product_uri = BK[product_id]
    
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        
        image = request.files['image']
        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join(os.path.dirname(__file__), 'static', 'images', filename))
        else:
            filename = g.value(product_uri, BK.image)
        
        for p, o in g.predicate_objects(product_uri):
            g.remove((product_uri, p, o))
        
        g.add((product_uri, RDF.type, BK.Product))
        g.add((product_uri, BK.name, Literal(name)))
        g.add((product_uri, BK.price, Literal(price)))
        g.add((product_uri, BK.description, Literal(description)))
        g.add((product_uri, BK.image, Literal(filename)))
        
        save_products_to_ttl()
        
        return redirect(url_for('products'))
    
    product = {
        'id': product_id,
        'name': g.value(product_uri, BK.name),
        'price': float(g.value(product_uri, BK.price)),
        'description': g.value(product_uri, BK.description),
        'image': g.value(product_uri, BK.image)
    }
    
    return render_template('admin/product_form.html', product=product)

@app.route('/admin/product/delete/<product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    product_uri = BK[product_id]
    
    for p, o in g.predicate_objects(product_uri):
        g.remove((product_uri, p, o))
    
    save_products_to_ttl()
    
    return redirect(url_for('products'))

@app.route('/admin/receipts')
@admin_required
def receipts():
    receipts = []
    records_dir = os.path.join(os.path.dirname(__file__), "records")
    
    if os.path.exists(records_dir):
        for filename in os.listdir(records_dir):
            if filename.startswith('order_') and filename.endswith('.xml'):
                tree = ET.parse(os.path.join(records_dir, filename))
                root = tree.getroot()
                
                order_id = filename[6:-4]
                date = datetime.fromisoformat(root.find('date').text)
                customer = root.find('customer')
                customer_name = customer.find('name').text
                total = float(root.find('total').text)
                
                receipts.append({
                    'id': order_id,
                    'date': date,
                    'customer_name': customer_name,
                    'total_amount': total
                })
    
    receipts.sort(key=lambda x: x['date'], reverse=True)
    return render_template('admin/receipts.html', receipts=receipts)

@app.route('/admin/receipt/<receipt_id>')
@admin_required
def view_receipt(receipt_id):
    receipt_data = generate_receipt_data(receipt_id)
    if receipt_data is None:
        return "Receipt not found", 404
    
    return render_template('admin/view_receipt.html', receipt=receipt_data)
