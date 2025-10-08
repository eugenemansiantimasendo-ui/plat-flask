from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:issaelde@localhost:5432/db_reservation'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'une_cle_secrete'

# Extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ----------------- MODELS -----------------
class Client(db.Model):
    __tablename__ = 'clients'
    id_client = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100))  # Ajouté
    email = db.Column(db.String(100), nullable=False, unique=True)
    telephone = db.Column(db.String(20))
    mot_de_passe = db.Column(db.String(200))  # Ajouté
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    reservations = db.relationship('Reservation', backref='client', cascade='all, delete-orphan')


class Categorie(db.Model):
    __tablename__ = 'categorie'
    categorie_id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)


class Plat(db.Model):
    __tablename__ = 'plats'
    id_plat = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    categorie = db.Column(db.String(50))
    prix = db.Column(db.Numeric(7,2), nullable=False)
    image_url = db.Column(db.Text)


class Reservation(db.Model):
    __tablename__ = 'reservations'
    id_reservation = db.Column(db.Integer, primary_key=True)
    id_client = db.Column(db.Integer, db.ForeignKey('clients.id_client', ondelete='CASCADE'), nullable=False)
    date_reservation = db.Column(db.Date, nullable=False)
    heure_reservation = db.Column(db.Time, nullable=False)
    nombre_personnes = db.Column(db.Integer, default=1)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='en attente')


class ReservationItem(db.Model):
    __tablename__ = 'reservation_items'
    id_item = db.Column(db.Integer, primary_key=True)
    id_reservation = db.Column(db.Integer, db.ForeignKey('reservations.id_reservation', ondelete='CASCADE'), nullable=False)
    plat_id = db.Column(db.Integer, db.ForeignKey('plats.id_plat', ondelete='CASCADE'), nullable=False)
    quantite = db.Column(db.Integer, default=1, nullable=False)

    reservation = db.relationship('Reservation', backref=db.backref('items', cascade='all, delete-orphan'))
    plat = db.relationship('Plat', backref=db.backref('reservation_items', cascade='all, delete-orphan'))


# ----------------- ROUTES -----------------
@app.route('/')
def index():
    clients = Client.query.all()
    plats = Plat.query.all()
    reservations = Reservation.query.all()
    return render_template('index.html', clients=clients, plats=plats, reservations=reservations)


# ---------- INSCRIPTION ----------
@app.route('/client/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        email = request.form.get('email')
        telephone = request.form.get('telephone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return redirect(url_for('inscription'))

        hashed_password = generate_password_hash(password)

        new_client = Client(
            nom=nom,
            prenom=prenom,
            email=email,
            telephone=telephone,
            mot_de_passe=hashed_password
        )
        db.session.add(new_client)
        db.session.commit()

        flash("Inscription réussie ! Connectez-vous.", "success")
        return redirect(url_for('connexion'))

    return render_template('plat/inscription.html')


# ---------- CONNEXION ----------
@app.route('/client/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        client = Client.query.filter_by(email=email).first()

        if client and check_password_hash(client.mot_de_passe, password):
            session['client_id'] = client.id_client
            flash(f"Bienvenue {client.nom} !", "success")
            return redirect(url_for('profil'))
        else:
            flash("Email ou mot de passe incorrect.", "danger")
            return redirect(url_for('connexion'))

    return render_template('plat/connexion.html')


# ---------- PROFIL ----------
@app.route('/client/profil')
def profil():
    if 'client_id' not in session:
        flash("Veuillez vous connecter.", "warning")
        return redirect(url_for('connexion'))

    client = Client.query.get(session['client_id'])
    return render_template('plat/profil.html', client=client)


if __name__ == '__main__':
    app.run(debug=True)
