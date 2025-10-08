# app.py
from flask import Flask, render_template, redirect, url_for, request, flash, g, session
from werkzeug.security import generate_password_hash
from flask_mail import Message

# -------------------------------
# Import des extensions et modèles
# -------------------------------
from extensions import db, migrate, mail
from models import Plat, Categorie, Contact, Reservation, Avis, Client

# -------------------------------
# Import des Blueprints
# -------------------------------
from routes.categorie import categorie_bp
from routes.clients import client_bp
from routes.dashboard import dashboard_bp
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
    app.config.update(
        SQLALCHEMY_DATABASE_URI='postgresql://mansiantima:issaelde@localhost:5432/db_reservation',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY='super-secret-key',
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME='ton.email@gmail.com',  # à remplacer
        MAIL_PASSWORD='ton_mot_de_passe'      # à remplacer
    )

    # -------------------------------
    # Initialisation des extensions
    # -------------------------------
    db.init_app(app)
    migrate.init_app(app, db)  # initialisation de Flask-Migrate
    mail.init_app(app)

    # -------------------------------
    # Gestion de l'utilisateur connecté
    # -------------------------------
    @app.before_request
    def load_logged_in_client():
        client_id = session.get('client_id')
        if client_id:
            g.client = Client.query.get(client_id)
        else:
            g.client = None

    @app.context_processor
    def inject_current_user():
        """Ajoute current_user au contexte Jinja pour éviter les erreurs dans les templates"""
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
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(client_bp, url_prefix='/clients')
    app.register_blueprint(plat_bp, url_prefix='/plats-admin')
    app.register_blueprint(categorie_bp, url_prefix='/categories')
    app.register_blueprint(reservation_bp, url_prefix='/reservation')
    app.register_blueprint(reservation_items_bp, url_prefix='/details-reservation')
    app.register_blueprint(plats_public_bp, url_prefix='/plats')
    app.register_blueprint(reservation_public_bp, url_prefix='/reservation-public')

    # -------------------------------
    # Routes principales
    # -------------------------------
    @app.route('/')
    def index():
        return redirect(url_for('dashboard.index'))

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            nom = request.form.get('nom')
            email = request.form.get('email')
            message_text = request.form.get('message')
            agent_email = request.form.get('agent')

            if not nom or not email or not message_text:
                flash("Veuillez remplir tous les champs.", "danger")
                return redirect(url_for('contact'))

            try:
                nouveau_message = Contact(
                    nom=nom,
                    email=email,
                    message=message_text,
                    agent=agent_email
                )
                db.session.add(nouveau_message)
                db.session.commit()

                # Envoi de mail à l’agent
                if agent_email:
                    msg = Message(
                        subject=f"Nouveau message de {nom}",
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[agent_email],
                        body=f"Vous avez reçu un nouveau message :\n\nNom : {nom}\nEmail : {email}\nMessage :\n{message_text}"
                    )
                    mail.send(msg)

                flash("Votre message a été envoyé avec succès !", "success")

            except Exception as e:
                db.session.rollback()
                print("Erreur BDD ou email:", e)
                flash("Une erreur est survenue, veuillez réessayer.", "danger")

            return redirect(url_for('contact'))

        return render_template('contact.html')

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
    # Hashage des mots de passe temporaires
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

    # -------------------------------
    # Page d’aide
    # -------------------------------
    @app.route('/aide')
    def aide():
        return render_template('aide.html')

    return app

# -------------------------------
# Lancement de l'application
# -------------------------------
if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()  # S’assure que la base est prête
    app.run(host='0.0.0.0', port=5000, debug=True)
