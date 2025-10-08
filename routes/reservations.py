from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from models import db, Client, Reservation, ReservationItem, Plat
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white
from reportlab.lib.utils import ImageReader
import qrcode
from datetime import datetime

reservation_bp = Blueprint(
    'reservation',
    __name__,
    template_folder='../templates/reservations'
)

# -----------------------------
# Liste des réservations avec recherche + pagination
# -----------------------------
@reservation_bp.route('/', methods=['GET'])
def liste_reservations():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = Reservation.query.join(Client)
    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(
            (Client.nom.ilike(f"%{search}%")) |
            (Client.email.ilike(f"%{search}%")) |
            (Client.telephone.ilike(f"%{search}%"))
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'liste_reservations.html',
        reservations=pagination.items,
        pagination=pagination,
        search=search
    )

# -----------------------------
# Ajouter une réservation
# -----------------------------
@reservation_bp.route('/ajouter', methods=['GET', 'POST'])
def ajouter_reservation():
    clients = Client.query.order_by(Client.nom).all()
    if request.method == 'POST':
        id_client = request.form.get('id_client')
        if id_client:
            client = Client.query.get(id_client)
            if not client:
                flash("Client non trouvé.", "danger")
                return redirect(url_for('reservation.ajouter_reservation'))
        else:
            nom = (request.form.get('nom') or '').strip()
            email = (request.form.get('email') or '').strip()
            telephone = (request.form.get('telephone') or '').strip()

            if not nom or not email:
                flash("Le nom et l'email sont obligatoires.", "danger")
                return redirect(url_for('reservation.ajouter_reservation'))

            client = Client.query.filter_by(email=email).first()
            if not client:
                client = Client(nom=nom, email=email, telephone=telephone)
                db.session.add(client)
                db.session.flush()

        try:
            nombre_personnes = int(request.form.get('nombre_personnes', 1))
        except ValueError:
            nombre_personnes = 1

        date_reservation = request.form.get('date_reservation') or datetime.now().date()
        heure_reservation = request.form.get('heure_reservation') or datetime.now().time()

        reservation = Reservation(
            id_client=client.id_client,
            date_reservation=date_reservation,
            heure_reservation=heure_reservation,
            nombre_personnes=nombre_personnes,
            message=request.form.get('message'),
            status=request.form.get('status', 'En attente')
        )
        db.session.add(reservation)
        try:
            db.session.commit()
            flash("Réservation ajoutée avec succès !", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Erreur lors de l'ajout de la réservation.", "danger")
        return redirect(url_for('reservation.liste_reservations'))

    return render_template('ajouter_reservation.html', clients=clients)

# -----------------------------
# Modifier une réservation
# -----------------------------
@reservation_bp.route('/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_reservation(id):
    reservation = Reservation.query.get_or_404(id)
    clients = Client.query.order_by(Client.nom).all()

    if request.method == 'POST':
        id_client = request.form.get('id_client')
        if id_client:
            client = Client.query.get(id_client)
            if not client:
                flash("Client non trouvé.", "danger")
                return redirect(url_for('reservation.modifier_reservation', id=id))
            reservation.id_client = client.id_client

        try:
            reservation.nombre_personnes = int(request.form.get('nombre_personnes', 1))
        except ValueError:
            reservation.nombre_personnes = 1

        reservation.date_reservation = request.form.get('date_reservation') or reservation.date_reservation
        reservation.heure_reservation = request.form.get('heure_reservation') or reservation.heure_reservation
        reservation.message = request.form.get('message', reservation.message)
        reservation.status = request.form.get('status') or reservation.status

        try:
            db.session.commit()
            flash("Réservation modifiée avec succès !", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Erreur lors de la modification de la réservation.", "danger")

        return redirect(url_for('reservation.liste_reservations'))

    return render_template('modifier_reservation.html', reservation=reservation, clients=clients)

# -----------------------------
# Supprimer une réservation
# -----------------------------
@reservation_bp.route('/supprimer/<int:id>', methods=['POST'])
def supprimer_reservation(id):
    reservation = Reservation.query.get_or_404(id)
    db.session.delete(reservation)
    db.session.commit()
    flash("Réservation supprimée avec succès !", "success")
    return redirect(url_for('reservation.liste_reservations'))

# -----------------------------
# Liste des plats réservés avec stats
# -----------------------------
@reservation_bp.route('/plats_reserves', methods=['GET'])
def liste_plats_reserves():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = ReservationItem.query.join(Reservation).join(Client).join(Plat)
    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(
            (Client.nom.ilike(f"%{search}%")) |
            (Client.email.ilike(f"%{search}%")) |
            (Client.telephone.ilike(f"%{search}%")) |
            (Plat.nom.ilike(f"%{search}%"))
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = pagination.items

    # Totaux
    total_qte = query.with_entities(func.sum(ReservationItem.quantite)).scalar() or 0
    clients = query.with_entities(func.count(func.distinct(Client.id_client))).scalar() or 0
    montant_total = query.with_entities(func.sum(ReservationItem.quantite * Plat.prix)).scalar() or 0.0
    montant_total = float(montant_total)

    return render_template(
        'reservation_items/liste_plats_reserves.html',
        items=items,
        pagination=pagination,
        total_qte=total_qte,
        clients=clients,
        montant_total=montant_total,
        search=search
    )

# -----------------------------
# Télécharger ticket PDF avec QR code
# -----------------------------
@reservation_bp.route('/telecharger_ticket/<int:reservation_id>')
def telecharger_ticket(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    # Bandeau noir avec titre centré
    c.setFillColor(black)
    c.rect(0, 800, 600, 40, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(300, 812, f"Ticket Réservation #{reservation.id_reservation}")

    # Infos réservation
    c.setFillColor(black)
    c.setFont("Helvetica", 12)
    c.drawString(50, 760, f"Client : {reservation.client.nom}")
    c.drawString(50, 740, f"Téléphone : {reservation.client.telephone}")
    c.drawString(50, 720, f"Date : {reservation.date_reservation}")
    c.drawString(50, 700, f"Heure : {reservation.heure_reservation}")
    c.drawString(50, 680, f"Nombre de personnes : {reservation.nombre_personnes}")

    # Liste des plats réservés + calcul total
    y = 660
    montant_total = 0
    if hasattr(reservation, 'items') and reservation.items:
        for item in reservation.items:
            plat_nom = item.plat.nom if item.plat else "Plat inconnu"
            quantite = float(item.quantite or 0)
            prix = float(item.plat.prix if item.plat else 0.0)
            total = quantite * prix
            montant_total += total
            c.drawString(50, y, f"{plat_nom} x {quantite} - {prix:.2f}$ = {total:.2f}$")
            y -= 20
    else:
        c.drawString(50, y, "Aucun plat réservé.")
        y -= 20

    # Montant total
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y - 10, f"Montant total : {montant_total:.2f} $")

    # QR code
    qr = qrcode.QRCode(box_size=3)
    qr.add_data(f"RESERVATION-{reservation.id_reservation}")
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_reader = ImageReader(img_qr)
    c.drawImage(qr_reader, 400, 650, width=120, height=120)

    c.showPage()
    c.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"ticket_{reservation.id_reservation}.pdf",
        mimetype='application/pdf'
    )
