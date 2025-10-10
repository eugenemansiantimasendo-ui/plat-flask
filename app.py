import os
import urllib.parse  # <-- pour encoder les caractères spéciaux dans le mot de passe
from flask import Flask, render_template, redirect, url_for, request, flash, g, session
from werkzeug.security import generate_password_hash
from flask_mail import Message
from datetime import datetime
from sqlalchemy import func

# -------------------------------
# Import des extensions et modèles
# -------------------------------
from extensions import db, migrate, mail
from models import Plat, Categorie, Contact, Reservation, Avis, Client, ReservationItem

# -------------------------------
# Import des Blueprints
# -------------------------------
from routes.categorie import categorie_bp
from routes.clients import client_bp
from routes.index import index_bp
from routes.plat import plat_bp
from routes.reservation_items import reservation_items_bp
from routes.reservations import reservation_bp
from routes.plats_publics import plats_public_bp
from routes.reservation_public import reservation_public_bp

# -------------------------------
# Fonction de création de l'application
# -------------------------------
def create_app():
    app = Flask(__name__)

    # -------------------------------
    # Configuration BDD et Mail
    # -------------------------------
    db_user = "mansiantima"
    db_password = urllib.parse.quote_plus("issaelde")  
    db_host = "localhost"
    db_port = "5432"
    db_name = "db_reservation"

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key')
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

    # -------------------------------
    # Initialisation des extensions
    # -------------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # -------------------------------
    # Gestion de l'utilisateur connecté
    # -------------------------------
    @app.before_request
    def load_logged_in_client():
        client_id = session.get('client_id')
        g.client = Client.query.get(client_id) if client_id else None

    @app.context_processor
    def inject_current_user():
        return dict(current_user=g.client)

    # -------------------------------
    # Filtres Jinja2 personnalisés
    # -------------------------------
    @app.template_filter('format_date')
    def format_date(value, format='%d/%m/%Y'):
        if not value:
            return ''
        try:
            return value.strftime(format)
        except Exception:
            return str(value)

    @app.template_filter('enumerate')
    def enumerate_filter(seq):
        return enumerate(seq)

    # -------------------------------
    # Enregistrement des Blueprints
    # -------------------------------
    app.register_blueprint(index_bp, url_prefix='/dashboard')
    app.register_blueprint(client_bp, url_prefix='/clients')
    app.register_blueprint(plat_bp, url_prefix='/plats-admin')
    app.register_blueprint(categorie_bp, url_prefix='/categories')
    app.register_blueprint(reservation_bp, url_prefix='/reservation')
    app.register_blueprint(reservation_items_bp, url_prefix='/details-reservation')
    app.register_blueprint(plats_public_bp, url_prefix='/plats')
    app.register_blueprint(reservation_public_bp, url_prefix='/reservation-public')

    # -------------------------------
    # Routes publiques
    # -------------------------------
    @app.route('/')
    def home():
        nb_clients = Client.query.count()
        nb_plats = Plat.query.count()
        nb_categories = Categorie.query.count()
        nb_reservations = Reservation.query.count()
        nb_serv_items = ReservationItem.query.count()

        nb_clients_servis = db.session.query(Client.id_client)\
            .join(Reservation, Reservation.id_client == Client.id_client)\
            .distinct().count()

        derniers_clients = Client.query.order_by(Client.date_creation.desc()).limit(5).all()
        dernieres_reservations = Reservation.query.order_by(Reservation.date_reservation.desc()).limit(5).all()

        mois_labels = [datetime(2025, m, 1).strftime('%B') for m in range(1, 13)]
        reservations_par_mois = [
            Reservation.query.filter(func.extract('month', Reservation.date_reservation) == m).count()
            for m in range(1, 13)
        ]

        categories = Categorie.query.all()
        top_categories = {
            "labels": [cat.nom for cat in categories],
            "data": [len(cat.plats) if hasattr(cat, 'plats') else 0 for cat in categories]
        }

        return render_template(
            'dashboard/index.html',
            nb_clients=nb_clients,
            nb_plats=nb_plats,
            nb_categories=nb_categories,
            nb_reservations=nb_reservations,
            nb_serv_items=nb_serv_items,
            nb_clients_servis=nb_clients_servis,
            derniers_clients=derniers_clients,
            dernieres_reservations=dernieres_reservations,
            mois_labels=mois_labels,
            reservations_par_mois=reservations_par_mois,
            top_categories=top_categories,
            plats=Plat.query.all()
        )

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            nom = request.form.get('nom', '').strip()
            email = request.form.get('email', '').strip()
            message_text = request.form.get('message', '').strip()
            agent_email = request.form.get('agent', '').strip()

            if not nom or not email or not message_text:
                flash("Veuillez remplir tous les champs.", "danger")
                return redirect(url_for('contact'))

            try:
                contact_msg = Contact(
                    nom=nom,
                    email=email,
                    message=message_text,
                    agent=agent_email or None
                )
                db.session.add(contact_msg)
                db.session.commit()

                if agent_email:
                    msg = Message(
                        subject=f"Nouveau message de {nom}",
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[agent_email],
                        body=f"Vous avez reçu un nouveau message :\n\n"
                             f"Nom : {nom}\nEmail : {email}\nMessage :\n{message_text}"
                    )
                    mail.send(msg)

                flash("Votre message a été envoyé avec succès !", "success")

            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erreur BDD ou email: {e}")
                flash("Une erreur est survenue, veuillez réessayer.", "danger")

            return redirect(url_for('contact'))

        return render_template('contact.html')

    @app.route('/aide')
    def aide():
        return render_template('aide.html')

    # -------------------------------
    # Gestion des erreurs
    # -------------------------------
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    # -------------------------------
    # Commande CLI : hashage des mots de passe
    # -------------------------------
    @app.cli.command('hash_temp_passwords')
    def hasher_mots_de_passe_temporaire():
        clients_temp = Client.query.filter_by(mot_de_passe="motdepasse_temporaire").all()
        if not clients_temp:
            print("Aucun mot de passe temporaire trouvé.")
            return
        for client in clients_temp:
            client.mot_de_passe = generate_password_hash("motdepasse_temporaire")
            print(f"Mot de passe hashé pour : {client.email}")
        db.session.commit()
        print("Tous les mots de passe temporaires ont été hashés.")

    return app

# -------------------------------
# Instance globale
# -------------------------------
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Création automatique des tables si elles n'existent pas

    port = int(os.environ.get("PORT", 5000))  # Port dynamique pour Render
    app.run(debug=False, host='0.0.0.0', port=port)
