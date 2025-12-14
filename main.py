from flask import Flask, render_template, request, session, redirect, url_for, flash
import os
from datetime import datetime
import logging
from urllib.parse import quote_plus
from functools import wraps # Import nécessaire pour la fonction login_required (si utilisée plus tard)

# --- Configuration du logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- MongoDB Setup ---
try:
    from pymongo import MongoClient
    from bson.objectid import ObjectId

    # URI de connexion fournie par l'utilisateur
    MONGO_URI = "mongodb+srv://ladeuxiemebanane_db_user:PRbjP1WLFIEi7HHy@cluster0.ybqtkvc.mongodb.net/?appName=Cluster0"
    DB_NAME = "musiqhub_db"

    # Initialisation du client MongoDB
    # Utiliser serverSelectionTimeoutMS pour éviter que l'application ne se bloque si MongoDB est injoignable
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    announcement_collection = db["announcements"]
    # Vérification de la connexion (simple ping)
    client.admin.command('ping')
    logging.info("Connexion à MongoDB réussie.")
    MONGO_READY = True
except Exception as e:
    logging.error(f"Erreur de connexion à MongoDB: {e}. Le site fonctionnera en mode limité/sans persistence.")
    MONGO_READY = False

# --- App Setup ---
app = Flask(__name__)
# Clé secrète pour les sessions Flask
app.secret_key = os.environ.get('MUSIQHUB_SECRET_KEY', 'dev-secret-change-me')

# --- Utility Functions for Auth (Simplified for Demo) ---

# Base de données d'utilisateurs simplifiée (À REMPLACER par une gestion sécurisée en production)
USERS = {
    "admin@musiqhub.com": {"password": "adminpassword", "username": "AdminMusiq"},
    "user@musiqhub.com": {"password": "userpassword", "username": "MusicFan"},
    "newuser@musiqhub.com": {"password": "PRbjP1WLFIEi7HHy", "username": "NouvelUtilisateur"}
}
# NOTE: Nous allons modifier la base de données USERS directement pour l'enregistrement.
# Dans une vraie application, cela irait dans MongoDB.

def get_current_user():
    """Récupère les informations de l'utilisateur connecté via la session."""
    user_email = session.get('user_email')
    if user_email in USERS:
        return {"email": user_email, "username": USERS[user_email]["username"]}
    return None

def is_logged_in():
    """Vérifie si un utilisateur est connecté."""
    return 'user_email' in session and session['user_email'] in USERS

# Fonction de décorateur pour s'assurer que l'utilisateur est connecté avant d'accéder à une route
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash("Vous devez être connecté pour accéder à cette page.", 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_globals():
    """Injecte des variables globales dans tous les templates."""
    return {
        'now': datetime.now,
        'user': get_current_user(),
        'is_logged_in': is_logged_in()
    }

# --- Routes d'Authentification ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Inscription utilisateur."""
    if is_logged_in():
        flash("Vous êtes déjà connecté.", 'info')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        # Validation basique
        if not username or not email or not password:
            flash("Tous les champs sont requis.", 'error')
            return render_template('register_form.html', username=username, email=email)

        if email in USERS:
            flash("Cet email est déjà utilisé.", 'error')
            return render_template('register_form.html', username=username, email=email)
        
        # Enregistrement de l'utilisateur (Simplifié: en RAM)
        USERS[email] = {"password": password, "username": username}
        logging.info(f"Nouvel utilisateur enregistré: {email}")

        # Connexion automatique après l'enregistrement
        session['user_email'] = email
        flash("Compte créé et connexion réussie!", 'success')
        return redirect(url_for('index'))
    
    return render_template('register_form.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Connexion utilisateur."""
    if is_logged_in():
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_data = USERS.get(email)
        if user_data and user_data["password"] == password:
            session['user_email'] = email
            flash("Connexion réussie.", 'success')
            return redirect(url_for('index'))
        else:
            flash("Email ou mot de passe incorrect.", 'error')
            return render_template('login_form.html', email=email)
    
    return render_template('login_form.html')

@app.route('/logout')
def logout():
    """Déconnexion utilisateur."""
    session.pop('user_email', None)
    flash("Vous avez été déconnecté.", 'info')
    return redirect(url_for('index'))

# --- Routes Principales et Genre ---

@app.route('/')
def index():
    """Page d'accueil - Liste des genres disponibles."""
    genres = [
        {'name': 'Pop', 'key': 'pop', 'emoji': '🎤'},
        {'name': 'Rock', 'key': 'rock', 'emoji': '🤘'},
        {'name': 'Hip-Hop', 'key': 'hiphop', 'emoji': '🎤'},
        {'name': 'Jazz', 'key': 'jazz', 'emoji': '🎺'},
        {'name': 'Électronique', 'key': 'electronique', 'emoji': '🎧'}
    ]
    return render_template('index.html', genres=genres)

@app.route('/genre/<genre_name>')
def genre_page(genre_name):
    """Affiche les annonces pour un genre spécifique."""
    genre_key = genre_name.lower().replace('é', 'e').replace('-', '')
    
    genre_info = {
        'pop': {'title': 'Pop', 'emoji': '🎤', 'color': '#2b0219'},
        'rock': {'title': 'Rock', 'emoji': '🤘', 'color': '#2a0505'},
        'hiphop': {'title': 'Hip-Hop', 'emoji': '🎤', 'color': '#45350b'},
        'jazz': {'title': 'Jazz', 'emoji': '🎺', 'color': '#02102b'},
        'electronique': {'title': 'Électronique', 'emoji': '🎧', 'color': '#052022'},
    }.get(genre_key, {'title': genre_name, 'emoji': '🎵', 'color': '#333333'})
    
    announcements = []
    if MONGO_READY:
        try:
            # Récupérer les annonces triées par date descendante
            announcements = list(announcement_collection.find(
                {"genre": genre_key}
            ).sort("timestamp", -1))
            
            # Formattage pour le template
            for a in announcements:
                a['_id'] = str(a['_id'])
                # S'assurer que 'timestamp' est une chaîne valide pour fromisoformat (ce qui est le cas avec isoformat())
                try:
                    a['display_date'] = datetime.fromisoformat(a['timestamp']).strftime('%d/%m/%Y à %H:%M')
                except (ValueError, TypeError):
                    a['display_date'] = 'Date inconnue'

        except Exception as e:
            logging.error(f"Erreur lors du chargement des annonces pour {genre_key}: {e}")
            flash(f"Erreur lors du chargement des annonces: {e}", 'error')
            
    return render_template(
        'genre_template.html',
        genre_name=genre_info['title'],
        genre_key=genre_key,
        genre_info=genre_info,
        announcements=announcements
    )

@app.route('/add_annonce/<genre_name>', methods=['POST'])
@login_required # S'assure que seul un utilisateur connecté peut poster
def add_annonce(genre_name):
    """Ajouter une nouvelle annonce pour le genre spécifié."""
    if not MONGO_READY:
        flash("La base de données n'est pas connectée. Annonce non enregistrée.", 'error')
        return redirect(url_for('genre_page', genre_name=genre_name))

    genre_key = genre_name.lower().replace('é', 'e').replace('-', '')
    
    user = get_current_user()
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    
    if not title or not content:
        flash("Le titre et le contenu de l'annonce ne peuvent pas être vides.", 'error')
        return redirect(url_for('genre_page', genre_name=genre_name))

    new_annonce = {
        "title": title,
        "content": content,
        "genre": genre_key,
        "author_email": user['email'],
        "author_username": user['username'],
        "timestamp": datetime.now().isoformat(),
    }
    
    try:
        announcement_collection.insert_one(new_annonce)
        flash(f"Annonce ajoutée avec succès au genre {genre_name}!", 'success')
    except Exception as e:
        logging.error(f"Erreur lors de l'insertion de l'annonce: {e}")
        flash(f"Erreur lors de l'ajout de l'annonce: {e}", 'error')
        
    return redirect(url_for('genre_page', genre_name=genre_name))


@app.errorhandler(404)
def page_not_found(e):
    """Page d'erreur 404."""
    return render_template('404.html'), 404


# **********************************************
# * BLOC DE LANCEMENT DE L'APPLICATION FLASK *
# **********************************************
if __name__ == '__main__':
    # Lance l'application sur http://127.0.0.1:5000/
    # debug=True permet le rechargement automatique lors des modifications de code
    app.run(debug=True)