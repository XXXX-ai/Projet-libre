from flask import Flask, render_template, request, session, redirect, url_for, flash
import os
from datetime import datetime
import logging
from urllib.parse import quote_plus
from functools import wraps

# --- Configuration du logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- MongoDB Setup ---
try:
    from pymongo import MongoClient
    from bson.objectid import ObjectId


    MONGO_URI = "mongodb+srv://ladeuxiemebanane_db_user:PRbjP1WLFIEi7HHy@cluster0.ybqtkvc.mongodb.net/?appName=Cluster0"
    DB_NAME = "musiqhub_db"

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    announcement_collection = db["announcements"]
    client.admin.command('ping')
    logging.info("Connexion à MongoDB réussie.")
    MONGO_READY = True
except Exception as e:
    logging.error(f"Erreur de connexion à MongoDB: {e}. Le site fonctionnera en mode limité/sans persistence.")
    MONGO_READY = False


app = Flask(__name__)
app.secret_key = os.environ.get('MUSIQHUB_SECRET_KEY', 'dev-secret-change-me')

USERS = {
    "AdminMusiq": {"password": "adminpassword"},
    "MusicFan": {"password": "userpassword"},
    "NouvelUtilisateur": {"password": "PRbjP1WLFIEi7HHy"}
}


def get_current_user():
    """Récupère les informations de l'utilisateur connecté via la session."""
    username = session.get('username')
    if username in USERS:
        return {"username": username}
    return None

def is_logged_in():
    """Vérifie si un utilisateur est connecté."""
    return 'username' in session and session['username'] in USERS

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
        password = request.form.get('password', '')
        
        if not username or not password:
            flash("Tous les champs sont requis.", 'error')
            return render_template('register_form.html', username=username)

        if username in USERS:
            flash("Ce nom d'utilisateur est déjà utilisé.", 'error')
            return render_template('register_form.html', username=username)
        
        USERS[username] = {"password": password}
        logging.info(f"Nouvel utilisateur enregistré: {username}")

        session['username'] = username
        flash("Compte créé et connexion réussie!", 'success')
        return redirect(url_for('index'))
    
    return render_template('register_form.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Connexion utilisateur."""
    if is_logged_in():
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = USERS.get(username)
        if user_data and user_data["password"] == password:
            session['username'] = username
            flash("Connexion réussie.", 'success')
            return redirect(url_for('index'))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect.", 'error')
            return render_template('login_form.html', username=username)
    
    return render_template('login_form.html')

@app.route('/logout')
def logout():
    """Déconnexion utilisateur."""
    session.pop('username', None)
    flash("Vous avez été déconnecté.", 'info')
    return redirect(url_for('index'))

@app.route('/')
def index():
    """Page d'accueil - Liste des genres disponibles et dernières actualités."""
    genres = [
        {'name': 'Pop', 'key': 'pop', 'emoji': '🎤', 'color': '#2b0219'}, # Ajout des couleurs pour réutilisation
        {'name': 'Rock', 'key': 'rock', 'emoji': '🤘', 'color': '#2a0505'},
        {'name': 'Hip-Hop', 'key': 'hiphop', 'emoji': '🎤', 'color': '#45350b'},
        {'name': 'Jazz', 'key': 'jazz', 'emoji': '🎺', 'color': '#02102b'},
        {'name': 'Électronique', 'key': 'electronique', 'emoji': '🎧', 'color': '#052022'}
    ]
    
    genre_map = {g['key']: g for g in genres} # Map des genres pour lookup rapide
    
    search_query = request.args.get('q', '').strip()
    actualites_data = []

    if MONGO_READY:
        try:
            # Création du filtre de recherche MongoDB
            mongo_filter = {}
            if search_query:
                # Utilisation d'une regex insensible à la casse pour titre ou contenu
                # $options: 'i' pour rendre la recherche insensible à la casse
                mongo_filter = {
                    "$or": [
                        {"title": {"$regex": search_query, "$options": "i"}},
                        {"content": {"$regex": search_query, "$options": "i"}}
                    ]
                }

            actualites_data = list(announcement_collection.find(
                mongo_filter
            ).sort("timestamp", -1).limit(15)) # Limite à 15 actualités

            for actualite in actualites_data:
                actualite['_id'] = str(actualite['_id'])
                # Ajout des infos de genre et de formatage de date
                genre_key = actualite['genre']
                if genre_key in genre_map:
                    actualite['genre_name'] = genre_map[genre_key]['name']
                    actualite['genre_emoji'] = genre_map[genre_key]['emoji']
                    actualite['genre_key'] = genre_key # Ajout de la clé pour l'URL
                else:
                    actualite['genre_name'] = 'Inconnu'
                    actualite['genre_emoji'] = '❓'
                    actualite['genre_key'] = 'inconnu'


                try:
                    actualite['display_date'] = datetime.fromisoformat(actualite['timestamp']).strftime('%d/%m/%Y à %H:%M')
                except (ValueError, TypeError):
                    actualite['display_date'] = 'Date inconnue'


        except Exception as e:
            logging.error(f"Erreur lors du chargement ou de la recherche des actualités: {e}")
            flash(f"Erreur lors du chargement des actualités: {e}", 'error')

    return render_template(
        'index.html', 
        genres=genres,
        actualites_data=actualites_data,
        search_query=search_query
    )

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
            announcements = list(announcement_collection.find(
                {"genre": genre_key}
            ).sort("timestamp", -1))
            
            for a in announcements:
                a['_id'] = str(a['_id'])
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
@login_required
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
#   BLOC DE LANCEMENT DE L'APPLICATION FLASK
# **********************************************
if __name__ == '__main__':

    app.run(debug=True)