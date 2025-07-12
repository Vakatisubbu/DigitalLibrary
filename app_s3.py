from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from db_config import db_config
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename
import uuid
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# S3 Config
S3_BUCKET = 'ccitpublicbucket'
S3_REGION = 'eu-west-2'
S3_ACCESS_KEY = ' '
S3_SECRET_KEY = ' '

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION
)

def upload_file_to_s3(file, bucket_name, acl="public-read"):
    try:
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"

        s3_client.upload_fileobj(
            file,
            bucket_name,
            unique_filename,
            ExtraArgs={
                "ACL": acl,
                "ContentType": file.content_type
            }
        )

        return f"https://{bucket_name}.s3.{S3_REGION}.amazonaws.com/{unique_filename}"

    except ClientError as e:
        print(f"S3 upload failed: {e}")
        return None

def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Validate all required fields are present
        required_fields = ['name', 'mobile', 'email', 'password', 're_password', 'gender', 'location']
        if not all(field in request.form for field in required_fields):
            flash('Please fill all required fields')
            return redirect(url_for('signup'))

        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        password = request.form['password']
        re_password = request.form['re_password']
        gender = request.form['gender']
        location = request.form['location']
        user_image = request.files.get('image')

        if password != re_password:
            flash('Passwords do not match')
            return redirect(url_for('signup'))

        image_url = None
        if user_image and user_image.filename != '':
            image_url = upload_file_to_s3(user_image, S3_BUCKET)
            if not image_url:
                return redirect(url_for('signup'))

        conn = get_db_connection()
        if not conn:
            flash('Database connection error')
            return redirect(url_for('signup'))

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('Email already exists')
                return redirect(url_for('signup'))

            cursor.execute("""
                INSERT INTO users (name, mobile, email, password, gender, location, image)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, mobile, email, password, gender, location, image_url))
            conn.commit()
            flash('Signup successful! Please login.')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            conn.rollback()
            flash('Database error occurred')
            print(f"Database Error: {err}")
        except Exception as e:
            conn.rollback()
            flash('System error occurred')
            print(f"Unexpected Error: {e}")
        finally:
            cursor.close()
            conn.close()

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect(url_for('welcome'))
        else:
            flash('Invalid email or password')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/welcome')
def welcome():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('welcome.html', user=user)

@app.route('/user', methods=['GET', 'POST'])
def user_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        book_id = request.form.get('book_id')

        if not action or not book_id:
            flash('Invalid action or book ID')
            return redirect(url_for('user_page'))

        user_id = session['user_id']

        if action == 'borrow':
            # Check if already borrowed and not returned
            cursor.execute("""
                SELECT COUNT(*) FROM history 
                WHERE user_id = %s AND book_id = %s AND return_date IS NULL
            """, (user_id, book_id))
            if cursor.fetchone()[0]:
                flash('You already borrowed this book and not yet returned.')
            else:
                cursor.execute("""
                    INSERT INTO history (user_id, book_id, borrow_date)
                    VALUES (%s, %s, %s)
                """, (user_id, book_id, datetime.now()))
                conn.commit()
                flash('Book borrowed successfully.')

        elif action == 'return':
            # Update return date of the latest borrowed entry
            cursor.execute("""
                SELECT id FROM history 
                WHERE user_id = %s AND book_id = %s AND return_date IS NULL 
                ORDER BY borrow_date DESC LIMIT 1
            """, (user_id, book_id))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    UPDATE history SET return_date = %s WHERE id = %s
                """, (datetime.now(), row[0]))
                conn.commit()
                flash('Book returned successfully.')
            else:
                flash('No borrowed record found to return.')

        return redirect(url_for('user_page'))

    # Load data for GET request
    user_id = session['user_id']

    cursor.execute("SELECT id, title, author FROM books")
    books = cursor.fetchall()

    cursor.execute("""
        SELECT b.id, b.title, b.author FROM history h
        JOIN books b ON h.book_id = b.id
        WHERE h.user_id = %s AND h.return_date IS NULL
    """, (user_id,))
    borrowed_books = cursor.fetchall()

    cursor.execute("""
        SELECT b.title, b.author, h.borrow_date, h.return_date, b.id FROM history h
        JOIN books b ON h.book_id = b.id
        WHERE h.user_id = %s
        ORDER BY h.borrow_date DESC
    """, (user_id,))
    history = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('user.html', books=books,
                           borrowed_books=borrowed_books,
                           history=history)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)