from flask import Flask, render_template, request, session, redirect, url_for, flash
import os
import json
from datetime import datetime
import re
from uuid import uuid4

app = Flask(__name__)

app.secret_key = os.environ.get('MUSIQHUB_SECRET_KEY', 'dev-secret-change-me')

@app.context_processor
def inject_datetime():
    return {'now': datetime.now}


DATA_FILE = os.path.join(app.root_path, 'data', 'actualites.json')

UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def load_actualites():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure list
            if isinstance(data, list):
                # Sort by timestamp descending when available
                try:
                    data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                except Exception:
                    pass
                return data
    except FileNotFoundError:
        return []
    except Exception:
        return []


@app.route('/')
def index():
    """Page d'accueil avec toutes les actualités (lecture seule depuis JSON)."""
    search_query = request.args.get('q', '').strip()

    actualites_data = load_actualites()

    if search_query:
        regex = re.compile(re.escape(search_query), re.IGNORECASE)
        actualites_data = [a for a in actualites_data if regex.search(a.get('titre', '')) or regex.search(a.get('description', ''))]

    return render_template('index.html', actualites=actualites_data, search_query=search_query)


@app.route('/genre/<genre>')
def genre_page(genre):
    """Affiche les actualités d'un genre spécifique."""
    genres_valides = ["Pop", "Rock", "Hip-Hop", "Jazz", "Électronique"]
    
    if genre not in genres_valides:
        flash("Genre invalide.", 'error')
        return redirect(url_for('index'))
    
    search_query = request.args.get('q', '').strip()

    # Lecture seule depuis le fichier JSON
    actualites_data = load_actualites()
    actualites_data = [a for a in actualites_data if a.get('genre') == genre]

    if search_query:
        regex = re.compile(re.escape(search_query), re.IGNORECASE)
        actualites_data = [a for a in actualites_data if regex.search(a.get('titre', '')) or regex.search(a.get('description', ''))]

    template_map = {
        "Pop": "/templates/pop.html",
        "Rock": "./rock.html",
        "Hip-Hop": "./hiphop.html",
        "Jazz": "jazz_page.html",
        "Électronique": "electro.html"
    }
    
    return render_template(template_map.get(genre, 'index.html'), 
                           actualites=actualites_data, 
                           search_query=search_query,
                           genre=genre)


@app.route("/login", methods=['GET', 'POST'])
def login():
    """Connexion utilisateur."""
    # Authentification désactivée: gestion des utilisateurs via scripts uniquement
    flash("La connexion via l'application web est désactivée. Utilisez les scripts d'administration.", 'info')
    return redirect(url_for('index'))


@app.route("/signin", methods=['GET', 'POST'])
def signin():
    """Inscription utilisateur."""
    # Inscription désactivée: gérer les comptes via les scripts si besoin
    flash("L'inscription via l'application web est désactivée. Utilisez les scripts d'administration.", 'info')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """Déconnexion utilisateur."""
    session.pop('User', None)
    flash("Vous avez été déconnecté.", 'info')
    return redirect(url_for('index'))


@app.route('/ajouter-actualite', methods=['GET', 'POST'])
def add_actualite():
    """Ajouter une nouvelle actualité."""
    # Les ajouts via l'interface web sont désactivés. Utilisez le script `scripts/manage_actualites.py`.
    flash("La publication d'actualités via le site est désactivée. Utilisez `scripts/manage_actualites.py`.", 'error')
    return redirect(url_for('index'))


@app.route('/supprimer-actualite/<actualite_id>', methods=['POST'])
def supprimer_actualite(actualite_id):
    """Supprimer une actualité."""
    # Suppression désactivée via web. Utilisez le script d'administration.
    flash("La suppression d'actualités via le site est désactivée. Utilisez `scripts/manage_actualites.py`.", 'error')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
