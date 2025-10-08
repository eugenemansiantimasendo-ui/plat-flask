from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from models import Plat, Categorie, Client, Avis, db
from datetime import datetime

# Blueprint pour les plats publics
plats_public_bp = Blueprint('plats_public', __name__)

# --------------------------
# Afficher le menu
# --------------------------
@plats_public_bp.route('/menu')
def afficher_menu():
    client = Client.query.get(session['client_id']) if session.get('client_id') else None
    categories = Categorie.query.all()
    selected_categorie = request.args.get('categorie', type=int)

    if selected_categorie:
        plats = Plat.query.filter_by(categorie_id=selected_categorie).all()
    else:
        plats = Plat.query.all()

    return render_template(
        'plat/menu.html',
        client=client,
        plats=plats,
        categories=categories,
        selected_categorie=selected_categorie
    )

# --------------------------
# Ajouter un avis classique (reload)
# --------------------------
@plats_public_bp.route('/plats_public/ajouter_avis', methods=['POST'])
def ajouter_avis():
    if not session.get('client_id'):
        flash("Vous devez être connecté pour laisser un avis.", "warning")
        return redirect(url_for('plats_public.afficher_menu'))

    try:
        plat_id = int(request.form.get('plat_id'))
        note = int(request.form.get('note'))
        commentaire = request.form.get('commentaire')
        id_client = int(session.get('client_id'))

        avis = Avis(
            id_plat=plat_id,
            id_client=id_client,
            note=note,
            commentaire=commentaire,
            date_avis=datetime.now()
        )
        db.session.add(avis)
        db.session.commit()
        flash("Votre avis a été ajouté avec succès !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de l'ajout de l'avis : {e}", "danger")

    return redirect(url_for('plats_public.afficher_menu'))

# --------------------------
# Ajouter un avis AJAX (sans reload)
# --------------------------
@plats_public_bp.route('/plats_public/ajouter_avis_ajax', methods=['POST'])
def ajouter_avis_ajax():
    if not session.get('client_id'):
        return jsonify({"success": False, "message": "Vous devez être connecté pour laisser un avis."})

    try:
        plat_id = int(request.form.get('plat_id'))
        note = int(request.form.get('note'))
        commentaire = request.form.get('commentaire')
        id_client = int(session.get('client_id'))

        # Création de l'avis
        avis = Avis(
            id_plat=plat_id,
            id_client=id_client,
            note=note,
            commentaire=commentaire,
            date_avis=datetime.now()
        )
        db.session.add(avis)
        db.session.commit()

        # Récupérer le nom du client pour l'affichage
        client = Client.query.get(id_client)

        # Calculer le total des notes et nombre d'avis pour mise à jour moyenne
        plats_avis = Avis.query.filter_by(id_plat=plat_id).all()
        total_notes = sum(a.note for a in plats_avis)
        nb_avis = len(plats_avis)

        return jsonify({
            "success": True,
            "avis": {
                "client": client.nom if client else "Anonyme",  # affichage du nom
                "note": note,
                "commentaire": commentaire,
                "date": avis.date_avis.strftime('%d/%m/%Y %H:%M')
            },
            "totalNotes": total_notes,
            "nbAvis": nb_avis
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})
