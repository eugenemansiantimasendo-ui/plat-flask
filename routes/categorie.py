from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Categorie
import os

# Blueprint pour les catégories
categorie_bp = Blueprint(
    'categorie', 
    __name__, 
    template_folder=os.path.join('templates', 'categories')  # dossier des templates
)

# ------------------------
# Liste des catégories triée par ID
# ------------------------
@categorie_bp.route('/', methods=['GET'])
def liste_categorie():
    categories = Categorie.query.order_by(Categorie.categorie_id).all()  # tri par ID réel
    return render_template('categories/liste_categorie.html', categories=categories)

# ------------------------
# Ajouter une catégorie
# ------------------------
@categorie_bp.route('/ajouter', methods=['GET', 'POST'])
def ajouter_categorie():
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        if nom:
            # Vérifie si la catégorie existe déjà
            existing = Categorie.query.filter_by(nom=nom).first()
            if existing:
                flash('Cette catégorie existe déjà.', 'warning')
                return redirect(url_for('categorie.liste_categorie'))
            
            cat = Categorie(nom=nom)
            db.session.add(cat)
            db.session.commit()
            flash('Catégorie ajoutée avec succès !', 'success')
            return redirect(url_for('categorie.liste_categorie'))
        flash('Le nom de la catégorie est requis.', 'danger')
    return render_template('categories/ajouter_categorie.html')

# ------------------------
# Modifier une catégorie
# ------------------------
@categorie_bp.route('/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_categorie(id):
    cat = Categorie.query.get_or_404(id)
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        if nom:
            # Vérifie si une autre catégorie avec le même nom existe
            existing = Categorie.query.filter(Categorie.nom==nom, Categorie.categorie_id!=id).first()
            if existing:
                flash('Une autre catégorie porte déjà ce nom.', 'warning')
                return redirect(url_for('categorie.liste_categorie'))
            
            cat.nom = nom
            db.session.commit()
            flash('Catégorie modifiée avec succès !', 'success')
            return redirect(url_for('categorie.liste_categorie'))
        flash('Le nom de la catégorie est requis.', 'danger')
    return render_template('categories/modifier_categorie.html', categorie=cat)

# ------------------------
# Supprimer une catégorie
# ------------------------
@categorie_bp.route('/supprimer/<int:id>', methods=['POST'])
def supprimer_categorie(id):
    cat = Categorie.query.get_or_404(id)
    if hasattr(cat, 'plats') and cat.plats:
        flash("Impossible de supprimer cette catégorie car elle contient des plats.", 'warning')
        return redirect(url_for('categorie.liste_categorie'))
    db.session.delete(cat)
    db.session.commit()
    flash('Catégorie supprimée avec succès !', 'success')
    return redirect(url_for('categorie.liste_categorie'))
