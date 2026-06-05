import os
import pymysql
import dj_database_url
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_mail import Mail, Message
from threading import Thread 
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy import func

# Load Environment variables
load_dotenv()

#1. App Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'development_fallback_key')

app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'

#--- TMDB API CONFIG ---
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

#--- FLASK-MAIL CONFIG ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)


#2. Database Setup
ENV = os.getenv('ENV', 'local')

if ENV == 'production':
    pymysql.install_as_MySQLdb()
    
    prod_db_url = os.getenv('DATABASE_URL')
    
    if prod_db_url and prod_db_url.startswith('mysql://'):
        prod_db_url = prod_db_url.replace('mysql://', 'mysql+pymysql://')
        
    app.config['SQLALCHEMY_DATABASE_URI'] = prod_db_url
    
    # TiDB Serverless requires SSL but accepts the system/certifi CA bundle
    import certifi
    import ssl
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "connect_args": {
            "ssl": ssl_ctx
        }
    }
else:
    db_user = os.getenv('LOCAL_DB_USER', 'root')
    db_password = os.getenv('LOCAL_DB_PASSWORD', '')
    db_host = os.getenv('LOCAL_DB_HOST', 'localhost')
    db_name = os.getenv('LOCAL_DB_NAME', 'movieapp')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


#3. User login Model
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    theme = db.Column(db.String(250), nullable=False, default='system')
    
    email = db.Column(db.String(150), unique=True, nullable=True)
    full_name = db.Column(db.String(150), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    avatar = db.Column(db.String(500), nullable=True)
    join_date = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)

# Favorites Model
class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    movie_id = db.Column(db.Integer, nullable=False)
    movie_title = db.Column(db.String(500), nullable=False)
    movie_poster = db.Column(db.String(500))
    added_date = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('Users', backref=db.backref('favorites', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


# Function to fetch popular movies
def get_popular_movies(endpoint):
    url = f"{TMDB_BASE_URL}/{endpoint}?api_key={TMDB_API_KEY}&language=en-US&page=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['results'][:20]
        else:
            return []
    except:
        return []

def get_movie_details(movie_id):
    url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None
    

#--- Function to send email ---
def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
            print(f'Async registration email sent successfully to {msg.recipients[0]}')
        except Exception as e:
            print(f'Failed to send async registration email: {e}')

def send_registration_email(recipient_email, username):
    try:
        html_body = render_template(
            'email/welcome.html', 
            username=username,
            login_url=url_for('login', _external=True),
            current_year=datetime.now().year
        )
        msg = Message(
            subject='Welcome to CineVerse! Account created successfully',
            recipients=[recipient_email],
            html=html_body
        )
        thr = Thread(target=send_async_email, args=[app, msg])
        thr.daemon = True
        thr.start()
        print(f'Email thread started for {recipient_email}')
        return thr
    except Exception as e:
        print(f'Failed to prepare registration email: {e}')
        return None


# Context processor for current year
@app.context_processor
def inject_year():
    return {'current_year': datetime.now().year}


# ============================================================
# CREATE TABLES ON STARTUP (works with both gunicorn and direct)
# ============================================================
with app.app_context():
    db.create_all()
    print("Database tables created/verified!")


#4. Routes
@app.route('/')
def home():
    trending_movies = get_popular_movies('trending/movie/week')
    popular_movies = get_popular_movies('movie/popular')[:8]
    return render_template('home.html', 
                         user=current_user, 
                         trending_movies=trending_movies, 
                         popular_movies=popular_movies,
                         image_base=TMDB_IMAGE_BASE)

#---Register---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email', '')
        full_name = request.form.get('full_name', '')

        existing_user = Users.query.filter((Users.username == username) | (Users.email == email)).first()
        if existing_user:
            flash('Username or email already exists!', 'error')
            return render_template('signup.html')
        
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = Users(
            username=username, 
            password=hashed_pw,
            email=email,
            full_name=full_name
        )
        db.session.add(new_user)
        db.session.commit()

        if email:
            send_registration_email(email, username)

        flash('Account Created! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

#---Login---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = Users.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
        
        user.last_login = datetime.now()
        db.session.commit()
        
        login_user(user)
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

#---Protected Page---
@app.route('/dashboard')
@login_required
def dashboard():
    trending_movies = get_popular_movies('trending/movie/week')
    popular_movies = get_popular_movies('movie/popular')
    upcoming_movies = get_popular_movies('movie/upcoming')
    
    return render_template('admin.html', 
                         user=current_user, 
                         trending_movies=trending_movies,
                         popular_movies=popular_movies,
                         upcoming_movies=upcoming_movies,
                         image_base=TMDB_IMAGE_BASE)


#---Logout---
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


#--- User Profile ---
@app.route('/profile')
@login_required
def profile():
    favorites_count = Favorite.query.filter_by(user_id=current_user.id).count()
    
    return render_template('profile.html',
                         user=current_user,
                         favorites_count=favorites_count)

#--- Update Profile ---
@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        current_user.full_name = request.form.get('full_name', '')
        current_user.email = request.form.get('email', '')
        current_user.bio = request.form.get('bio', '')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        flash('Error updating profile', 'error')
        print(f"Profile update error: {e}")
    
    return redirect(url_for('profile'))

#--- Update Avatar ---
@app.route('/update_avatar', methods=['POST'])
@login_required
def update_avatar():
    avatar_url = request.form.get('avatar_url', '')
    
    if avatar_url:
        current_user.avatar = avatar_url
        db.session.commit()
        flash('Avatar updated successfully!', 'success')
    else:
        flash('Please provide a valid avatar URL', 'error')
    
    return redirect(url_for('profile'))


#--- Movie Details Page ---
@app.route('/movie/<int:movie_id>')
def movie_details(movie_id):
    movie_url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
    movie_response = requests.get(movie_url)
    
    videos_url = f"{TMDB_BASE_URL}/movie/{movie_id}/videos?api_key={TMDB_API_KEY}&language=en-US"
    videos_response = requests.get(videos_url)
    
    similar_url = f"{TMDB_BASE_URL}/movie/{movie_id}/similar?api_key={TMDB_API_KEY}&language=en-US&page=1"
    similar_response = requests.get(similar_url)
    
    if movie_response.status_code == 200:
        movie = movie_response.json()
        videos = videos_response.json().get('results', []) if videos_response.status_code == 200 else []
        similar_movies = similar_response.json().get('results', [])[:8] if similar_response.status_code == 200 else []
        
        trailer = None
        for video in videos:
            if video['type'] == 'Trailer' and video['site'] == 'YouTube':
                trailer = video
                break
        
        return render_template('movie_details.html', 
                             movie=movie, 
                             trailer=trailer,
                             similar_movies=similar_movies,
                             image_base=TMDB_IMAGE_BASE,
                             user=current_user)
    else:
        flash('Movie not found!', 'error')
        return redirect(url_for('home'))
    

#--- Search Functionality ---
@app.route('/search')
def search():
    query = request.args.get('q', '')
    genre = request.args.get('genre', '')
    min_rating = request.args.get('min_rating', '')
    year = request.args.get('year', '')
    page = request.args.get('page', 1, type=int)
    
    base_url = f"{TMDB_BASE_URL}/discover/movie"
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'sort_by': 'popularity.desc',
        'page': page
    }
    
    if query:
        base_url = f"{TMDB_BASE_URL}/search/movie"
        params['query'] = query
    else:
        if genre:
            params['with_genres'] = genre
        if min_rating:
            params['vote_average.gte'] = min_rating
        if year:
            params['primary_release_year'] = year
    
    genres_url = f"{TMDB_BASE_URL}/genre/movie/list?api_key={TMDB_API_KEY}&language=en-US"
    genres_response = requests.get(genres_url)
    genres = genres_response.json().get('genres', []) if genres_response.status_code == 200 else []
    
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        movies = data['results']
        total_pages = min(data['total_pages'], 10)
        total_results = data['total_results']
    else:
        movies = []
        total_pages = 0
        total_results = 0
    
    return render_template('search.html',
                         movies=movies,
                         query=query,
                         genre=genre,
                         min_rating=min_rating,
                         year=year,
                         genres=genres,
                         page=page,
                         total_pages=total_pages,
                         total_results=total_results,
                         image_base=TMDB_IMAGE_BASE,
                         user=current_user)


#--- Add to Favorites ---
@app.route('/add_favorite/<int:movie_id>', methods=['POST'])
@login_required
def add_favorite(movie_id):
    movie_url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
    response = requests.get(movie_url)
    
    if response.status_code == 200:
        movie = response.json()
        
        existing_favorite = Favorite.query.filter_by(
            user_id=current_user.id, 
            movie_id=movie_id
        ).first()
        
        if existing_favorite:
            return jsonify({'success': False, 'message': 'Already in favorites'})
        
        new_favorite = Favorite(
            user_id=current_user.id,
            movie_id=movie_id,
            movie_title=movie['title'],
            movie_poster=movie['poster_path']
        )
        
        db.session.add(new_favorite)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Added to favorites'})
    else:
        return jsonify({'success': False, 'message': 'Movie not found'})

#--- Remove from Favorites ---
@app.route('/remove_favorite/<int:movie_id>', methods=['POST'])
@login_required
def remove_favorite(movie_id):
    favorite = Favorite.query.filter_by(
        user_id=current_user.id, 
        movie_id=movie_id
    ).first()
    
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Removed from favorites'})
    else:
        return jsonify({'success': False, 'message': 'Not in favorites'})

#--- Check Favorite Status ---
@app.route('/is_favorite/<int:movie_id>')
@login_required
def is_favorite(movie_id):
    favorite = Favorite.query.filter_by(
        user_id=current_user.id, 
        movie_id=movie_id
    ).first()
    
    return jsonify({'is_favorite': favorite is not None})

#--- Favorites Page ---
@app.route('/favorites')
@login_required
def favorites():
    user_favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    return render_template('favorites.html', 
                         favorites=user_favorites,
                         image_base=TMDB_IMAGE_BASE,
                         user=current_user)


@app.route('/set_theme', methods=['POST'])
def set_theme():
    try:
        payload = request.get_json(force=True)
        theme = payload.get('theme', '').lower()
        if theme not in ('light','dark','system'):
            return jsonify({"error":"invalid theme"}), 400

        if current_user.is_authenticated:
            current_user.theme = theme
            db.session.commit()
            return jsonify({"status":"ok", "saved_to_db": True})
        else:
            return jsonify({"status":"ok", "saved_to_db": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- CATCH-ALL ROUTE ---
@app.route('/<path:invalid_path>')
def catch_all(invalid_path):
    return redirect(url_for('home'))

#5. Run App
if __name__ == '__main__':
    app.run(debug=True)