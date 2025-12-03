from flask import Flask, render_template, request, session, redirect, url_for, flash
import pymongo
import os
import bcrypt
from datetime import datetime
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename 
import re 

app = Flask(__name__)

# Configuration MongoDB
client = pymongo.MongoClient("mongodb+srv://dbUser:<db_password>@cluster0.4r2wbaa.mongodb.net/?appName=Cluster0")
db = client["MusiqHub"]

app.secret_key = "Dx1S7hfG6W6kxthL" 

# Configuration des images
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.context_processor
def inject_datetime():
    return {'now': datetime.now}


def initialiser_donnees_principales():
    """Initialise les collections avec des données de démonstration."""
    actualites_collection = db["actualites"]
    
    if actualites_collection.count_documents({}) == 0:
        # Insère des actualités de démo par genre
        demo_actualites = [
            {
                "titre": "Taylor Swift annonce une nouvelle tournée mondiale",
                "description": "La superstar annonce 156 dates à travers le monde pour 2025 et 2026, avec de nouvelles scènes révolutionnaires.",
                "genre": "Pop",
                "auteur": "Admin",
                "date_publication": datetime.now().strftime("%d/%m/%Y à %H:%M"), 
                "image_url": None 
            },
            {
                "titre": "The Rolling Stones en concert à Paris",
                "description": "Les légendes du rock reviennent en France pour deux soirs exceptionnels à l'Accor Arena. Billets en pré-vente dès demain.",
                "genre": "Rock",
                "auteur": "Admin",
                "date_publication": datetime.now().strftime("%d/%m/%Y à %H:%M"), 
                "image_url": None 
            },
            {
                "titre": "Kendrick Lamar dévoile son nouvel album",
                "description": "Un album surprise est arrivé sans prévenir sur toutes les plateformes. 16 pistes de pur génie à découvrir.",
                "genre": "Hip-Hop",
                "auteur": "Admin",
                "date_publication": datetime.now().strftime("%d/%m/%Y à %H:%M"), 
                "image_url": None 
            },
            {
                "titre": "Festival de Jazz de Montreux 2025 programmation",
                "description": "Les plus grands noms du jazz se donnent rendez-vous en juillet au bord du lac Léman pour une édition exceptionnelle.",
                "genre": "Jazz",
                "auteur": "Admin",
                "date_publication": datetime.now().strftime("%d/%m/%Y à %H:%M"), 
                "image_url": None 
            },
            {
                "titre": "Daft Punk annonce un grand retour surprise",
                "description": "Les maîtres de l'électronique seraient en studio pour préparer un nouvel album révolutionnaire selon nos sources.",
                "genre": "Électronique",
                "auteur": "Admin",
                "date_publication": datetime.now().strftime("%d/%m/%Y à %H:%M"), 
                "image_url": None 
            }
        ]
        
        actualites_collection.insert_many(demo_actualites)
        print("Actualités de démo insérées dans MongoDB.")


with app.app_context():
    initialiser_donnees_principales()


@app.route('/')
def index():
    """Page d'accueil avec toutes les actualités."""
    search_query = request.args.get('q', '').strip()
    
    query_filter = {}

    if search_query:
        regex_pattern = re.compile(re.escape(search_query), re.IGNORECASE)
        query_filter = {
            "$or": [
                {"titre": {"$regex": regex_pattern}},
                {"description": {"$regex": regex_pattern}}
            ]
        }

    actualites_data = list(db["actualites"].find(query_filter).sort('date_publication', pymongo.DESCENDING))

    for a in actualites_data:
        try:
            a['id'] = str(a.get('_id'))
        except Exception:
            a['id'] = None

    return render_template('index.html', 
                           actualites=actualites_data, 
                           search_query=search_query) 


@app.route('/genre/<genre>')
def genre_page(genre):
    """Affiche les actualités d'un genre spécifique."""
    genres_valides = ["Pop", "Rock", "Hip-Hop", "Jazz", "Électronique"]
    
    if genre not in genres_valides:
        flash("Genre invalide.", 'error')
        return redirect(url_for('index'))
    
    search_query = request.args.get('q', '').strip()
    
    query_filter = {"genre": genre}

    if search_query:
        regex_pattern = re.compile(re.escape(search_query), re.IGNORECASE)
        query_filter["$or"] = [
            {"titre": {"$regex": regex_pattern}},
            {"description": {"$regex": regex_pattern}}
        ]

    actualites_data = list(db["actualites"].find(query_filter).sort('date_publication', pymongo.DESCENDING))

    for a in actualites_data:
        try:
            a['id'] = str(a.get('_id'))
        except Exception:
            a['id'] = None

    # Sélectionner le template approprié
    template_map = {
        "Pop": "pop.html",
        "Rock": "rock.html",
        "Hip-Hop": "hiphop.html",
        "Jazz": "jazz_page.html",
        "Électronique": "electro_page.html"
    }
    
    return render_template(template_map.get(genre, 'index.html'), 
                           actualites=actualites_data, 
                           search_query=search_query,
                           genre=genre)


@app.route("/login", methods=['GET', 'POST'])
def login():
    """Connexion utilisateur."""
    if request.method == 'POST':
        db_user = db["User"] 
        user = db_user.find_one({'user_id': request.form['user_id']})
        
        if user:
            hashed_password_from_db = str(user.get('user_password', '')).encode('utf-8')
            user_password_input = request.form['password'].encode('utf-8')
        
            try:
                if bcrypt.checkpw(user_password_input, hashed_password_from_db):
                    session['User'] = request.form['user_id']
                    flash('Connexion réussie !', 'success')
                    return redirect(url_for('index'))
                else:
                    flash("Identifiant ou mot de passe invalide.", 'error')
            except ValueError:
                flash("Identifiant ou mot de passe invalide.", 'error')
        else:
            flash("Identifiant ou mot de passe invalide.", 'error')
            
    return render_template('login.html')


@app.route("/signin", methods=['GET', 'POST'])
def signin():
    """Inscription utilisateur."""
    users_collection = db["User"]
    
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        
        if users_collection.find_one({'user_id': user_id}):
            flash('Cet identifiant est déjà pris. Veuillez en choisir un autre.', 'error')
            return redirect(url_for('signin'))
        else:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            hashed_password_str = hashed_password.decode('utf-8')
            users_collection.insert_one({
                'user_id': user_id,
                'user_password': hashed_password_str 
            })
            
            flash('Inscription réussie ! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))
    
    return render_template('signin.html')


@app.route('/logout')
def logout():
    """Déconnexion utilisateur."""
    session.pop('User', None)
    flash("Vous avez été déconnecté.", 'info')
    return redirect(url_for('index'))


@app.route('/ajouter-actualite', methods=['GET', 'POST'])
def add_actualite():
    """Ajouter une nouvelle actualité."""
    if 'User' not in session:
        flash("Vous devez être connecté pour publier une actualité.", 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        titre = request.form.get('titre')
        description = request.form.get('description')
        genre = request.form.get('genre')
        file = request.files.get('file')
        auteur = session['User']

        if not titre or not description or not genre:
            flash("Le titre, la description et le genre sont obligatoires.", 'error')
            return render_template('add_actualite.html')

        image_url = None

        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{auteur}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            try:
                file.save(filepath)
                image_url = os.path.join('uploads', unique_filename).replace('\\', '/')
            except Exception as e:
                print(f"Erreur lors de la sauvegarde du fichier : {e}")
                flash("Erreur lors du téléchargement de l'image. Veuillez réessayer.", 'error')
                image_url = None
        
        db["actualites"].insert_one({
            "titre": titre,
            "description": description,
            "genre": genre,
            "auteur": auteur,
            "date_publication": datetime.now().strftime("%d/%m/%Y à %H:%M"),
            "image_url": image_url 
        })

        flash("Votre actualité a été publiée avec succès !", 'success')
        return redirect(url_for('index'))

    genres = ["Pop", "Rock", "Hip-Hop", "Jazz", "Électronique"]
    return render_template('add_actualite.html', genres=genres)


@app.route('/supprimer-actualite/<actualite_id>', methods=['POST'])
def supprimer_actualite(actualite_id):
    """Supprimer une actualité."""
    if 'User' not in session:
        flash("Vous devez être connecté pour supprimer une actualité.", 'error')
        return redirect(url_for('login'))

    actualites_collection = db["actualites"]

    try:
        obj_id = ObjectId(actualite_id)
    except Exception:
        flash("Identifiant d'actualité invalide.", 'error')
        return redirect(url_for('index'))

    actualite = actualites_collection.find_one({'_id': obj_id})
    if not actualite:
        flash("Actualité introuvable.", 'error')
        return redirect(url_for('index'))

    current_user = session['User']

    if current_user != 'Admin' and actualite.get('auteur') != current_user:
        flash("Vous n'êtes pas autorisé à supprimer cette actualité.", 'error')
        return redirect(url_for('index'))
    
    image_url = actualite.get('image_url')
    if image_url:
        filepath = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], os.path.basename(image_url))
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"Fichier image supprimé : {filepath}")
            except Exception as e:
                print(f"Erreur lors de la suppression du fichier : {e}")

    actualites_collection.delete_one({'_id': obj_id})
    flash("Actualité supprimée.", 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
