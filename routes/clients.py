from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify, current_app
from models import db, Client, Plat, Reservation, ReservationItem, Categorie, Contact
from datetime import datetime, timedelta
import json, secrets
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_mail import Message

client_bp = Blueprint('client', __name__)

# -------------------------------
# Décorateur : connexion requise
# -------------------------------
def connexion_requise(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'client_id' not in session:
            flash("Veuillez vous connecter pour continuer.", "warning")
            return redirect(url_for('client.connexion'))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------------
# ADMINISTRATION - CRUD CLIENTS
# -------------------------------
@client_bp.route('/')
def liste_client():
    page = request.args.get('page', 1, type=int)
    clients = Client.query.order_by(Client.id_client).paginate(page=page, per_page=10)
    return render_template('clients/client.html', clients=clients)

@client_bp.route('/ajouter', methods=['GET', 'POST'])
def ajouter_client():
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        email = request.form.get('email', '').strip()
        telephone = request.form.get('telephone', '').strip()
        password = request.form.get('password', '').strip()

        if not nom or not email or not password:
            flash('Le nom, l’email et le mot de passe sont obligatoires.', 'danger')
            return redirect(url_for('client.ajouter_client'))

        # Vérification email et téléphone uniques
        if Client.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé par un autre client.', 'warning')
            return redirect(url_for('client.ajouter_client'))
        if telephone and Client.query.filter_by(telephone=telephone).first():
            flash('Ce numéro de téléphone est déjà utilisé par un autre client.', 'warning')
            return redirect(url_for('client.ajouter_client'))

        if telephone and not telephone.isdigit():
            flash('Le numéro de téléphone doit contenir uniquement des chiffres.', 'danger')
            return redirect(url_for('client.ajouter_client'))

        nouveau_client = Client(
            nom=nom,
            email=email,
            telephone=telephone,
            mot_de_passe=generate_password_hash(password)
        )
        try:
            db.session.add(nouveau_client)
            db.session.commit()
            flash('Client ajouté avec succès!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'ajout du client : {e}", 'danger')
        return redirect(url_for('client.liste_client'))

    return render_template('clients/ajouter_client.html')

@client_bp.route('/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_client(id):
    cli = Client.query.get_or_404(id)
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        email = request.form.get('email', '').strip()
        telephone = request.form.get('telephone', '').strip()

        if not nom or not email:
            flash('Le nom et l’email sont obligatoires.', 'danger')
            return redirect(url_for('client.modifier_client', id=id))

        if Client.query.filter(Client.email == email, Client.id_client != id).first():
            flash('Cet email est déjà utilisé par un autre client.', 'warning')
            return redirect(url_for('client.modifier_client', id=id))

        if telephone and not telephone.isdigit():
            flash('Le numéro de téléphone doit contenir uniquement des chiffres.', 'danger')
            return redirect(url_for('client.modifier_client', id=id))

        cli.nom = nom
        cli.email = email
        cli.telephone = telephone
        try:
            db.session.commit()
            flash('Client modifié avec succès!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la modification : {e}", 'danger')
        return redirect(url_for('client.liste_client'))

    return render_template('clients/modifier_client.html', client=cli)

@client_bp.route('/supprimer/<int:id>', methods=['POST'])
def supprimer_client(id):
    cli = Client.query.get_or_404(id)
    try:
        db.session.delete(cli)
        db.session.commit()
        flash('Client supprimé avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {e}", 'danger')
    return redirect(url_for('client.liste_client'))

# -------------------------------
# PROFIL / CÔTÉ CLIENT
# -------------------------------
@client_bp.route('/profil')
@connexion_requise
def profil():
    client = Client.query.get(session['client_id'])
    return render_template('profil/profil.html', client=client)

@client_bp.route('/modifier_profil', methods=['GET', 'POST'])
@connexion_requise
def modifier_profil():
    client = Client.query.get(session['client_id'])
    if request.method == 'POST':
        client.nom = request.form.get('nom', client.nom)
        client.prenom = request.form.get('prenom', client.prenom)
        client.email = request.form.get('email', client.email)
        client.telephone = request.form.get('telephone', client.telephone)
        password = request.form.get('password')
        if password:
            client.mot_de_passe = generate_password_hash(password)
        try:
            db.session.commit()
            flash('Profil mis à jour avec succès!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la mise à jour du profil : {e}", 'danger')
        return redirect(url_for('client.profil'))
    return render_template('profil/modifier_profil.html', client=client)

# -------------------------------
# MENU & COMMANDES
# -------------------------------
@client_bp.route('/menu')
@connexion_requise
def menu_client():
    plats = Plat.query.all()
    categories = Categorie.query.all()
    client = Client.query.get(session['client_id'])
    return render_template('plat/menu.html', plats=plats, categories=categories, client=client)

@client_bp.route('/mes_commandes')
@connexion_requise
def mes_commandes():
    client_id = session['client_id']
    reservations = Reservation.query.filter_by(id_client=client_id).order_by(Reservation.date_reservation.desc()).all()
    for r in reservations:
        r.total = sum(item.quantite * float(item.prix_unitaire) for item in r.items)
    client = Client.query.get(session['client_id'])
    return render_template('commandes/mes_commandes.html', commandes=reservations, client=client)

# -------------------------------
# PANIER
# -------------------------------
@client_bp.route('/panier_actuel')
@connexion_requise
def panier_actuel():
    panier = session.get('panier', [])
    return jsonify(panier)

@client_bp.route('/sauvegarder_panier', methods=['POST'])
@connexion_requise
def sauvegarder_panier():
    session['panier'] = request.get_json()
    session.modified = True
    return jsonify({"success": True})

@client_bp.route('/ajouter_commande_multiple', methods=['POST'])
@connexion_requise
def ajouter_commande_multiple():
    commande_data = request.form.get('commande_data')
    if not commande_data:
        return jsonify({"success": False, "message": "Données incomplètes"}), 400

    commande_items = json.loads(commande_data)
    client = Client.query.get(session['client_id'])

    now = datetime.now()
    reservation = Reservation(
        id_client=client.id_client,
        date_reservation=now.date(),
        heure_reservation=now.time(),
        status="En attente"
    )
    db.session.add(reservation)
    db.session.flush()

    for item in commande_items:
        plat = Plat.query.get(item['id'])
        if plat:
            ri = ReservationItem(
                id_reservation=reservation.id_reservation,
                plat_id=plat.id_plat,
                quantite=item['quantite'],
                prix_unitaire=plat.prix
            )
            db.session.add(ri)

    try:
        db.session.commit()
        session['panier'] = []
        return jsonify({
            "success": True,
            "client": {"nom": client.nom, "email": client.email, "tel": client.telephone},
            "plats_reserves": commande_items,
            "date_creation": str(reservation.date_reservation)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Erreur: {e}"}), 500

# -------------------------------
# CONNEXION / INSCRIPTION / DÉCONNEXION
# -------------------------------
@client_bp.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        client = Client.query.filter_by(email=email).first()

        if client and client.mot_de_passe and check_password_hash(client.mot_de_passe, password):
            session['client_id'] = client.id_client
            flash(f"Bienvenue {client.nom} !", "success")
            return redirect(url_for('client.menu_client'))
        flash("Email ou mot de passe incorrect.", "danger")
        return redirect(url_for('client.connexion'))
    return render_template('profil/connexion.html')

@client_bp.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        email = request.form.get('email')
        telephone = request.form.get('telephone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([nom, prenom, email, telephone, password, confirm_password]):
            flash("Veuillez remplir tous les champs.", "warning")
            return redirect(url_for('client.inscription'))

        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return redirect(url_for('client.inscription'))

        # Vérification email et téléphone uniques
        if Client.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé par un autre compte.", "warning")
            return redirect(url_for('client.inscription'))

        if Client.query.filter_by(telephone=telephone).first():
            flash("Ce numéro de téléphone est déjà utilisé par un autre compte.", "warning")
            return redirect(url_for('client.inscription'))

        new_client = Client(
            nom=nom,
            prenom=prenom,
            email=email,
            telephone=telephone,
            mot_de_passe=generate_password_hash(password)
        )
        try:
            db.session.add(new_client)
            db.session.commit()
            flash("Inscription réussie ! Connectez-vous.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'inscription : {e}", "danger")
        return redirect(url_for('client.connexion'))

    return render_template('profil/inscription.html')

@client_bp.route('/deconnexion')
def deconnexion():
    session.pop('client_id', None)
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for('client.connexion'))

# -------------------------------
# MOT DE PASSE OUBLIÉ / RÉINITIALISATION
# -------------------------------
@client_bp.route('/mot_de_passe_oublie', methods=['GET', 'POST'])
def mot_de_passe_oublie():
    reset_url = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash("Veuillez saisir un email.", "warning")
        else:
            client = Client.query.filter_by(email=email).first()
            if client:
                token = secrets.token_urlsafe(32)
                client.reset_token = token
                client.reset_token_expiration = datetime.utcnow() + timedelta(hours=1)
                db.session.commit()

                reset_url = url_for('client.reinitialiser_mot_de_passe', token=token, _external=True)
                flash("Un lien de réinitialisation a été généré.", "info")
                print(f"Lien de réinitialisation pour {client.email}: {reset_url}")
            else:
                flash("Aucun compte trouvé avec cet email.", "danger")

    return render_template('profil/mot_de_passe_oublie.html', reset_url=reset_url)

@client_bp.route('/reinitialiser_mot_de_passe/<token>', methods=['GET', 'POST'])
def reinitialiser_mot_de_passe(token):
    client = Client.query.filter_by(reset_token=token).first()
    if not client or datetime.utcnow() > client.reset_token_expiration:
        flash("Lien invalide ou expiré.", "danger")
        return redirect(url_for('client.mot_de_passe_oublie'))

    if request.method == 'POST':
        nouveau_mdp = request.form.get('password', '').strip()
        confirm_mdp = request.form.get('confirm_password', '').strip()
        if nouveau_mdp != confirm_mdp:
            flash("Les mots de passe ne correspondent pas.", "warning")
            return redirect(request.url)

        client.mot_de_passe = generate_password_hash(nouveau_mdp)
        client.reset_token = None
        client.reset_token_expiration = None
        db.session.commit()
        flash("Mot de passe mis à jour avec succès !", "success")
        return redirect(url_for('client.connexion'))

    return render_template('profil/reinitialiser_mot_de_passe.html', token=token)

# -------------------------------
# PAGES STATIQUES
# -------------------------------
@client_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        nom = request.form.get('nom')
        email = request.form.get('email')
        message = request.form.get('message')
        agent = request.form.get('agent')
        if not nom or not email or not message:
            flash("Veuillez remplir tous les champs.", "danger")
            return redirect(url_for('client.contact'))
        try:
            nouveau_message = Contact(nom=nom, email=email, message=message, agent=agent)
            db.session.add(nouveau_message)
            db.session.commit()
            flash("Votre message a été envoyé avec succès !", "success")
        except Exception as e:
            db.session.rollback()
            print("Erreur BDD:", e)
            flash("Une erreur est survenue, veuillez réessayer.", "danger")
        return redirect(url_for('client.contact'))
    return render_template('contact.html')

@client_bp.route('/aide')
def aide():
    return render_template('aide.html')
