from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from models import Plat, Categorie, Client, Avis, db
from datetime import datetime

plats_public_bp = Blueprint('plats_public', __name__)

# --------------------------
# Afficher le menu
# --------------------------
@plats_public_bp.route('/menu')
def afficher_menu():
    client = Client.query.get(session.get('client_id')) if session.get('client_id') else None
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
@plats_public_bp.route('/ajouter_avis', methods=['POST'])
def ajouter_avis():
    if not session.get('client_id'):
        flash("Vous devez être connecté pour laisser un avis.", "warning")
        return redirect(url_for('plats_public.afficher_menu'))

    try:
        plat_id = int(request.form.get('plat_id'))
        note = int(request.form.get('note'))
        commentaire = request.form.get('commentaire')
        id_client = int(session.get('client_id'))

        # Vérifier que le plat existe
        plat = Plat.query.get(plat_id)
        if not plat:
            flash("Le plat sélectionné n'existe pas.", "danger")
            return redirect(url_for('plats_public.afficher_menu'))

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
@plats_public_bp.route('/ajouter_avis_ajax', methods=['POST'])
def ajouter_avis_ajax():
    if not session.get('client_id'):
        return jsonify({"success": False, "message": "Vous devez être connecté pour laisser un avis."})

    try:
        plat_id = int(request.form.get('plat_id'))
        note = int(request.form.get('note'))
        commentaire = request.form.get('commentaire')
        id_client = int(session.get('client_id'))

        # Vérifier que le plat existe
        plat = Plat.query.get(plat_id)
        if not plat:
            return jsonify({"success": False, "message": "Le plat sélectionné n'existe pas."})

        avis = Avis(
            id_plat=plat_id,
            id_client=id_client,
            note=note,
            commentaire=commentaire,
            date_avis=datetime.now()
        )
        db.session.add(avis)
        db.session.commit()

        client = Client.query.get(id_client)

        # Calcul du total et du nombre d'avis
        total_notes = db.session.query(db.func.sum(Avis.note)).filter_by(id_plat=plat_id).scalar() or 0
        nb_avis = db.session.query(db.func.count(Avis.id_avis)).filter_by(id_plat=plat_id).scalar() or 0

        return jsonify({
            "success": True,
            "avis": {
                "client": client.nom if client else "Anonyme",
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
