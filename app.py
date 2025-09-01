from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os
from bson import ObjectId
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['Electronic']  # Database name
users = db.users
products = db.products
cart = db.cart
orders = db.orders
user_profiles = db.user_profiles  # New collection for user profiles

# Routes
@app.route('/')
def index():
    # Get featured products and new arrivals from database
    featured_products = list(products.find().limit(4))  # Get 4 products for featured section
    new_arrivals = list(products.find().sort('_id', -1).limit(4))  # Get 4 newest products
    
    # Convert ObjectId to string for each product
    for product in featured_products:
        product['_id'] = str(product['_id'])
    for product in new_arrivals:
        product['_id'] = str(product['_id'])
    
    return render_template('index.html', featured_products=featured_products, new_arrivals=new_arrivals)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not username or not email or not password or not confirm_password:
            flash('All fields are required', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return redirect(url_for('register'))
        
        # Username validation
        if not username.isalnum() or len(username) < 3:
            flash('Username must be at least 3 characters long and contain only letters and numbers', 'danger')
            return redirect(url_for('register'))
        
        # Email format validation
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            flash('Invalid email format', 'danger')
            return redirect(url_for('register'))
        
        try:
            # Check if user already exists
            if users.find_one({'email': email}):
                flash('Email already registered', 'danger')
                return redirect(url_for('register'))
            
            if users.find_one({'username': username}):
                flash('Username already taken', 'danger')
                return redirect(url_for('register'))
            
            # Create new user with enhanced structure
            new_user = {
                'username': username,
                'email': email,
                'password': generate_password_hash(password),
                'role': 'user',
                'date_joined': datetime.now(),
                'last_login': datetime.now(),
                'is_active': True,
                'profile': {
                    'first_name': '',
                    'last_name': '',
                    'phone': '',
                    'address': '',
                    'city': '',
                    'state': '',
                    'zip_code': '',
                    'profile_pic': '/static/images/default_profile.png'
                },
                'stats': {
                    'cart_items': 0,
                    'orders_count': 0,
                    'total_spent': 0.0,
                    'wishlist_count': 0
                },
                'settings': {
                    'email_notifications': True,
                    'order_updates': True,
                    'newsletter': True,
                    'two_factor_auth': False
                }
            }
            
            # Insert the new user
            result = users.insert_one(new_user)
            
            if result.inserted_id:
                # Create user profile
                user_profile = {
                    'user_id': result.inserted_id,
                    'email': email,
                    'first_name': '',
                    'last_name': '',
                    'phone': '',
                    'address': '',
                    'city': '',
                    'state': '',
                    'zip_code': '',
                    'shipping_addresses': [],
                    'billing_addresses': [],
                    'wishlist': [],
                    'viewed_products': [],
                    'favorite_categories': [],
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                user_profiles.insert_one(user_profile)
                
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Registration failed. Please try again.', 'danger')
                return redirect(url_for('register'))
                
        except Exception as e:
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember')
        
        if not email or not password:
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('login'))
        
        try:
            user = users.find_one({'email': email})
            
            if user and check_password_hash(user['password'], password):
                # Update user's last login time and session
                users.update_one(
                    {'_id': user['_id']},
                    {
                        '$set': {
                            'last_login': datetime.now(),
                            'is_active': True
                        }
                    }
                )
                
                # Set session variables
                session['user_id'] = str(user['_id'])
                session['username'] = user['username']
                session['email'] = user['email']
                session.permanent = True if remember else False
                
                flash('Logged in successfully!', 'success')
                
                # Redirect to the page user was trying to access, or home
                next_page = request.args.get('next')
                return redirect(next_page if next_page else url_for('index'))
            else:
                flash('Invalid email or password', 'danger')
                return redirect(url_for('login'))
                
        except Exception as e:
            flash('An error occurred during login. Please try again.', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        flash('Please login first!')
        return redirect(url_for('login'))
    
    user_cart = list(cart.find({'user_id': session['user_id']}))
    cart_items = []
    total = 0.0
    
    for item in user_cart:
        product = products.find_one({'_id': ObjectId(item['product_id'])})
        if product:
            # Ensure price is float
            product_price = float(product.get('price', 0.0))
            item_quantity = int(item.get('quantity', 1))
            item_total = product_price * item_quantity
            
            cart_items.append({
                'product': product,
                'quantity': item_quantity,
                'price': product_price,
                'total': item_total
            })
            total += item_total
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))
    
    user_cart = list(cart.find({'user_id': session['user_id']}))
    cart_items = []
    total = 0.0
    
    for item in user_cart:
        product = products.find_one({'_id': ObjectId(item['product_id'])})
        if product:
            product_price = float(product.get('price', 0.0))
            item_quantity = int(item.get('quantity', 1))
            item_total = product_price * item_quantity
            cart_items.append({
                'product': product,
                'quantity': item_quantity,
                'price': product_price,
                'total': item_total
            })
            total += item_total
    
    if request.method == 'POST':
        order_data = {
            'user_id': session['user_id'],
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'zip': request.form.get('zip'),
            'payment_method': request.form.get('payment_method'),
            'items': cart_items,
            'total': total,
            'status': 'pending',
            'date': datetime.now()
        }
        
        if 'orders' not in db.list_collection_names():
            db.create_collection('orders')
        
        db.orders.insert_one(order_data)
        cart.delete_many({'user_id': session['user_id']})
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_confirmation'))
    
    return render_template('checkout.html', cart_items=cart_items, total=total)

@app.route('/order-confirmation')
def order_confirmation():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('order_confirmation.html')

@app.route('/add_to_cart/<product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))
    
    quantity = int(request.form.get('quantity', 1))
    
    # Check if product already in cart
    existing_item = cart.find_one({
        'user_id': session['user_id'],
        'product_id': product_id
    })
    
    if existing_item:
        cart.update_one(
            {'_id': existing_item['_id']},
            {'$inc': {'quantity': quantity}}
        )
    else:
        cart.insert_one({
            'user_id': session['user_id'],
            'product_id': product_id,
            'quantity': quantity
        })
    
    flash('Product added to cart successfully!', 'success')
    return redirect(url_for('view_cart'))  # Redirect to cart page instead of index

@app.route('/update_cart/<product_id>', methods=['POST'])
def update_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    quantity_change = int(request.form.get('quantity_change', 0))
    
    # Find the cart item
    cart_item = cart.find_one({
        'user_id': session['user_id'],
        'product_id': product_id
    })
    
    if cart_item:
        new_quantity = cart_item['quantity'] + quantity_change
        if new_quantity > 0:
            # Update quantity
            cart.update_one(
                {'_id': cart_item['_id']},
                {'$set': {'quantity': new_quantity}}
            )
        else:
            # Remove item if quantity would be 0 or less
            cart.delete_one({'_id': cart_item['_id']})
    
    return redirect(url_for('view_cart'))

@app.route('/remove_from_cart/<product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Remove the item from cart
    cart.delete_one({
        'user_id': session['user_id'],
        'product_id': product_id
    })
    
    flash('Item removed from cart', 'success')
    return redirect(url_for('view_cart'))

# Initialize database collections and indexes
def init_db():
    # Initialize users collection with proper structure
    if 'users' not in db.list_collection_names():
        db.create_collection('users')
        # Create unique indexes for email and username
        users.create_index('email', unique=True)
        users.create_index('username', unique=True)
        
        # Create admin user
        admin_user = {
            'username': 'admin',
            'email': 'admin@example.com',
            'password': generate_password_hash('admin123'),
            'role': 'admin',
            'date_joined': datetime.now(),
            'last_login': datetime.now(),
            'is_active': True,
            'profile': {
                'first_name': 'Admin',
                'last_name': 'User',
                'phone': '',
                'address': '',
                'city': '',
                'state': '',
                'zip_code': '',
                'profile_pic': '/static/images/default_profile.png'
            },
            'stats': {
                'cart_items': 0,
                'orders_count': 0,
                'total_spent': 0.0,
                'wishlist_count': 0
            },
            'settings': {
                'email_notifications': True,
                'order_updates': True,
                'newsletter': False,
                'two_factor_auth': False
            }
        }
        users.insert_one(admin_user)

    # Initialize user_profiles collection for extended user data
    if 'user_profiles' not in db.list_collection_names():
        db.create_collection('user_profiles')
        user_profiles.create_index('user_id', unique=True)
        user_profiles.create_index('email', unique=True)
        
        # Create indexes for common search fields
        user_profiles.create_index([
            ('first_name', 'text'),
            ('last_name', 'text'),
            ('city', 'text'),
            ('state', 'text')
        ])

    # Drop and recreate products collection
    products.drop()
    
    sample_products = [
        {
            'name': 'Smartphone X',
            'description': 'Latest model smartphone with advanced features, 5G capability, and stunning camera system',
            'price': 699.99,
            'image': '/static/images/iphone 13 pro.png',
            'category': 'Smartphones'
        },
        {
            'name': 'Gaming Laptop Pro',
            'description': 'High-performance laptop with RTX 3080, 32GB RAM, and 1TB SSD',
            'price': 1299.99,
            'image': '/static/images/laptop2.png',
            'category': 'Laptops'
        },
        {
            'name': 'Wireless Headphones',
            'description': 'Premium wireless noise-canceling headphones with 30-hour battery life',
            'price': 199.99,
            'image': '/static/images/h1.png',
            'category': 'Audio'
        },
        {
            'name': '4K Smart TV',
            'description': '65-inch 4K Smart TV with HDR and built-in streaming apps',
            'price': 899.99,
            'image': '/static/images/pr1.png',
            'category': 'TVs'
        },
        {
            'name': 'Smartwatch',
            'description': 'Advanced smartwatch with health monitoring and GPS',
            'price': 299.99,
            'image': '/static/images/w1.png',
            'category': 'Wearables'
        },
        {
            'name': 'Wireless Earbuds',
            'description': 'True wireless earbuds with active noise cancellation',
            'price': 149.99,
            'image': '/static/images/pr3.png',
            'category': 'Audio'
        },
        {
            'name': 'Gaming Console',
            'description': 'Next-gen gaming console with 4K gaming capability',
            'price': 499.99,
            'image': '/static/images/pr8.png',
            'category': 'Gaming'
        },
        {
            'name': 'Tablet Pro',
            'description': '12.9-inch tablet with M1 chip and Liquid Retina XDR display',
            'price': 799.99,
            'image': '/static/images/t1.png',
            'category': 'Tablets'
        }
    ]
    
    # Insert products
    if products.count_documents({}) == 0:
        products.insert_many(sample_products)

    # Initialize cart collection
    if 'cart' not in db.list_collection_names():
        db.create_collection('cart')
        cart.create_index([('user_id', 1), ('product_id', 1)])

    # Initialize orders collection
    if 'orders' not in db.list_collection_names():
        db.create_collection('orders')
        orders.create_index('user_id')
        orders.create_index('date')
        orders.create_index([('status', 1), ('date', -1)])  # For order status queries

if __name__ == '__main__':
    init_db()  # Initialize sample products
    app.run(debug=True) 