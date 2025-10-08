import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from models import db, Plat, Categorie

# -------------------------------
# Blueprint pour les plats
# -------------------------------
plat_bp = Blueprint('plat', __name__)  # plus besoin de template_folder

# -------------------------------
# Dossier pour stocker les images
# -------------------------------
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------------
# Liste des plats triée par ID
# -------------------------------
@plat_bp.route('/', methods=['GET'])
def liste_plats():
    plats = Plat.query.order_by(Plat.id_plat).all()  # tri par ID
    return render_template('plat/liste_plats.html', plats=plats)

# -------------------------------
# Ajouter un plat
# -------------------------------
@plat_bp.route('/ajouter', methods=['GET', 'POST'])
def ajouter_plat():
    categories = Categorie.query.order_by(Categorie.nom).all()

    if request.method == 'POST':
        nom = request.form.get('nom')
        description = request.form.get('description')
        categorie_id = request.form.get('categorie_id')
        prix = request.form.get('prix')
        image = request.files.get('image')

        image_filename = None
        if image and image.filename != "":
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(UPLOAD_FOLDER, image_filename))

        plat = Plat(
            nom=nom,
            description=description,
            prix=prix,
            categorie_id=categorie_id,
            image_url=image_filename
        )

        db.session.add(plat)
        db.session.commit()
        flash(f"Le plat '{nom}' a été ajouté avec succès !", 'success')
        return redirect(url_for('plat.liste_plats'))

    return render_template('plat/ajouter_plat.html', categories=categories)

# -------------------------------
# Modifier un plat
# -------------------------------
@plat_bp.route('/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_plat(id):
    plat = Plat.query.get_or_404(id)
    categories = Categorie.query.order_by(Categorie.nom).all()

    if request.method == 'POST':
        plat.nom = request.form.get('nom')
        plat.description = request.form.get('description')
        plat.prix = request.form.get('prix')
        plat.categorie_id = request.form.get('categorie_id')

        image = request.files.get('image')
        if image and image.filename != "":
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(UPLOAD_FOLDER, image_filename))
            plat.image_url = image_filename

        db.session.commit()
        flash(f"Le plat '{plat.nom}' a été modifié avec succès !", 'success')
        return redirect(url_for('plat.liste_plats'))

    return render_template('plat/modifier_plat.html', plat=plat, categories=categories)

# -------------------------------
# Supprimer un plat
# -------------------------------
@plat_bp.route('/supprimer/<int:id>', methods=['POST'])
def supprimer_plat(id):
    plat = Plat.query.get_or_404(id)
    db.session.delete(plat)
    db.session.commit()
    flash(f"Le plat '{plat.nom}' a été supprimé.", 'danger')
    return redirect(url_for('plat.liste_plats'))
