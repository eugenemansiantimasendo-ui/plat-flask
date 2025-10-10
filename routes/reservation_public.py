from flask import Blueprint, request, redirect, url_for, flash, session, send_file, jsonify, render_template
from models import db, Client, Reservation, ReservationItem, Plat
import json
from datetime import datetime, date
import io, base64, qrcode
from weasyprint import HTML
from flask_mail import Message
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import qrcode
import base64
from flask import jsonify
from weasyprint import HTML
from extensions import mail



reservation_public_bp = Blueprint('reservation_public', __name__)

# -----------------------------
# Filtre Jinja pour échapper en JS
# -----------------------------
@reservation_public_bp.app_template_filter('escapejs')
def escapejs_filter(s):
    return json.dumps(s)

# -----------------------------
# Fonction utilitaire pour total d'une commande
# -----------------------------
def calcul_total(items):
    return sum(item.quantite * (item.prix_unitaire if item.prix_unitaire else (item.plat.prix if item.plat else 0)) for item in items)

# -----------------------------
# Génération QR code en base64
# -----------------------------
def generer_qr_b64(data):
    qr_img = qrcode.make(data)
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

# -----------------------------
# Ajouter un plat au panier (session)
# -----------------------------
@reservation_public_bp.route('/ajouter_panier', methods=['POST'])
def ajouter_panier():
    try:
        plat_id = int(request.form.get('plat_id', 0))
        nom = request.form.get('nom', '').strip()
        prix = float(request.form.get('prix', 0))
        quantite = int(request.form.get('quantite', 1))

        if not plat_id or not nom or quantite <= 0:
            flash("Données du plat invalides.", "danger")
            return redirect(request.referrer)

        panier = session.get('panier', [])
        for item in panier:
            if item['id'] == plat_id:
                item['quantite'] += quantite
                break
        else:
            panier.append({'id': plat_id, 'nom': nom, 'prix': prix, 'quantite': quantite})

        session['panier'] = panier
        session.modified = True
        flash(f"{nom} ajouté au panier !", "success")
        return redirect(request.referrer)
    except Exception as e:
        flash(f"Erreur lors de l'ajout au panier : {str(e)}", "danger")
        return redirect(request.referrer)

# -----------------------------
# Sauvegarder le panier côté session
# -----------------------------
@reservation_public_bp.route('/sauvegarder_panier', methods=['POST'])
def sauvegarder_panier():
    try:
        panier = request.get_json()
        for item in panier:
            item['id'] = int(item['id'])
            item['prix'] = float(item['prix'])
            item['quantite'] = int(item['quantite'])
        session['panier'] = panier
        session.modified = True
        # ✅ Retour JSON pour que le fetch côté JS fonctionne
        return jsonify({"success": True, "message": "Panier sauvegardé", "panier": session['panier']})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

# -----------------------------
# Récupérer le panier actuel
# -----------------------------
@reservation_public_bp.route('/panier-actuel')
def panier_actuel():
    return jsonify(session.get('panier', []))

# -----------------------------
# Afficher le panier
# -----------------------------
@reservation_public_bp.route('/mon_panier')
def mon_panier():
    panier = session.get('panier', [])
    total = sum(item['prix'] * item['quantite'] for item in panier)
    return render_template('panier/mon_panier.html', panier=panier, total=total)

# -----------------------------
# Afficher les commandes d’un client
# -----------------------------
@reservation_public_bp.route('/commandes')
def commandes():
    client_id = session.get('client_id')
    if not client_id:
        flash("Veuillez vous connecter pour voir vos commandes.", "warning")
        return redirect(url_for('reservation_public.mon_panier'))

    commandes = Reservation.query.filter_by(id_client=client_id).order_by(Reservation.date_reservation.desc()).all()
    commandes_list = []

    for cmd in commandes:
        items = []
        total = 0
        for item in cmd.items:
            prix_total_item = item.quantite * item.prix_unitaire
            items.append({
                'plat': item.plat,
                'quantite': item.quantite,
                'prix_unitaire': item.prix_unitaire,
                'total_item': prix_total_item
            })
            total += prix_total_item

        commandes_list.append({
            'id_reservation': cmd.id_reservation,
            'date_reservation': cmd.date_reservation,
            'status': getattr(cmd, 'status', 'En attente'),
            'items_commandes': items,
            'total': total
        })

    return render_template('commandes/mes_commandes.html', commandes=commandes_list)

# -----------------------------
# Ajouter une commande multiple depuis le panier
# -----------------------------
@reservation_public_bp.route('/ajouter_commande_multiple', methods=['POST'])
def ajouter_commande_multiple():
    try:
        nom_client = request.form.get('nom_client', '').strip()
        email_client = request.form.get('email_client', '').strip()
        tel_client = request.form.get('tel_client', '').strip()
        commande_data = request.form.get('commande_data', '')

        if not nom_client or not tel_client:
            return jsonify({'success': False, 'message': "Veuillez remplir votre nom et téléphone."})
        if not commande_data:
            return jsonify({'success': False, 'message': "Aucun plat sélectionné."})

        items = json.loads(commande_data)
        if not items:
            return jsonify({'success': False, 'message': "Le panier est vide."})

        client = Client.query.filter_by(telephone=tel_client).first()
        if not client:
            client = Client(
                nom=nom_client,
                email=email_client or f"{tel_client}@exemple.com",
                telephone=tel_client
            )
            db.session.add(client)
            db.session.flush()

        session['client_id'] = client.id_client
        now = datetime.now()
        reservation = Reservation(
            id_client=client.id_client,
            date_reservation=now.date(),
            heure_reservation=now.time(),
            qrcode_data=f"{client.id_client}_{now.timestamp()}"
        )
        db.session.add(reservation)
        db.session.flush()

        total_commande = 0
        items_ajoutes = 0
        for item in items:
            plat_id = item.get('id')
            quantite = int(item.get('quantite', 1))
            if not plat_id or quantite <= 0:
                continue
            plat = Plat.query.get(plat_id)
            if not plat:
                continue
            prix_unitaire = float(plat.prix) if plat.prix else 0.0
            total_commande += prix_unitaire * quantite
            res_item = ReservationItem(
                id_reservation=reservation.id_reservation,
                plat_id=plat.id_plat,
                quantite=quantite,
                prix_unitaire=prix_unitaire
            )
            db.session.add(res_item)
            items_ajoutes += 1

        if items_ajoutes == 0:
            db.session.rollback()
            return jsonify({'success': False, 'message': "Aucun plat valide pour la commande."})

        db.session.commit()
        session.pop('panier', None)
        session.modified = True

        return jsonify({
            'success': True,
            'reservation_id': reservation.id_reservation,
            'message': f"Commande validée avec succès ! Total : ${total_commande:.2f}"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f"Erreur lors de l'ajout de la commande : {str(e)}"})

# -----------------------------
# Afficher ticket HTML avec QR code
# -----------------------------
@reservation_public_bp.route('/ticket/<int:reservation_id>')
def ticket(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    client = reservation.client
    items = reservation.items

    if not items:
        flash("Aucun plat réservé pour cette réservation.", "warning")
        return redirect(url_for('reservation_public.mon_panier'))

    # Préparer le total correct
    total = sum(
        item.quantite * (item.prix_unitaire if item.prix_unitaire else (item.plat.prix if item.plat else 0))
        for item in items
    )

    # Générer QR code en base64
    qr_img = qrcode.make(reservation.qrcode_data)
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return render_template(
        "ticket_test.html",
        reservation=reservation,
        client=client,
        items=items,
        total=total,
        qr_b64=qr_b64
    )

# -----------------------------
# Télécharger ticket PDF
# -----------------------------
@reservation_public_bp.route('/telecharger_ticket/<int:reservation_id>')
def telecharger_ticket(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    client = reservation.client
    items = reservation.items
    if not items:
        flash("Impossible de générer le ticket : aucun plat réservé.", "warning")
        return redirect(url_for('reservation_public.mon_panier'))

    buffer = io.BytesIO()
    TICKET_WIDTH = 80 * mm
    LINE_HEIGHT = 4 * mm  # réduit pour serrer les lignes
    MARGIN = 4 * mm
    TICKET_HEIGHT = max(len(items) * LINE_HEIGHT + 120*mm, 150*mm)

    pdf = canvas.Canvas(buffer, pagesize=(TICKET_WIDTH, TICKET_HEIGHT))
    y = TICKET_HEIGHT

    # --- Header noir dès le début centré ---
    HEADER_HEIGHT = 18*mm
    pdf.setFillColorRGB(0.13, 0.13, 0.13)
    pdf.rect(0, y-HEADER_HEIGHT, TICKET_WIDTH, HEADER_HEIGHT, fill=1, stroke=0)
    pdf.setFillColorRGB(1,1,1)

    header_center_y = y - HEADER_HEIGHT/2
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(TICKET_WIDTH/2, header_center_y + 4, "🍽️ Restaurant Eugene")
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(TICKET_WIDTH/2, header_center_y - 4, f"Ticket #{reservation.id_reservation}")

    y -= HEADER_HEIGHT + 2*mm  # espace réduit après le header

    # --- Client ---
    pdf.setFont("Courier", 8)
    pdf.setFillColorRGB(0,0,0)
    pdf.drawString(MARGIN, y, f"Client: {client.nom if client else 'Inconnu'}")
    y -= LINE_HEIGHT
    pdf.drawString(MARGIN, y, f"Email: {client.email if client else 'Inconnu'}")
    y -= LINE_HEIGHT
    pdf.drawString(MARGIN, y, f"Tél: {client.telephone if client else 'Inconnu'}")
    y -= LINE_HEIGHT + 1*mm  # petit espace avant ligne perforée

    # --- Ligne perforée ---
    pdf.setDash(2,2)
    pdf.line(MARGIN, y, TICKET_WIDTH-MARGIN, y)
    pdf.setDash()
    y -= LINE_HEIGHT

    # --- Plats commandés ---
    pdf.setFont("Courier-Bold", 8)
    pdf.drawString(MARGIN, y, "Plats commandés:")
    y -= LINE_HEIGHT

    pdf.setFont("Courier", 8)
    total = 0
    for item in items:
        prix = item.prix_unitaire if item.prix_unitaire is not None else (item.plat.prix if item.plat else 0)
        item_total = item.quantite * prix
        total += item_total
        nom = item.plat.nom if item.plat else "Plat inconnu"
        pdf.drawString(MARGIN, y, f"{nom} x{item.quantite}")
        pdf.drawRightString(TICKET_WIDTH-MARGIN, y, f"${item_total:.2f}")
        y -= LINE_HEIGHT  # réduit pour serrer les plats

    # --- Ligne perforée ---
    y -= 1*mm
    pdf.setDash(2,2)
    pdf.line(MARGIN, y, TICKET_WIDTH-MARGIN, y)
    pdf.setDash()
    y -= LINE_HEIGHT

    # --- Total ---
    pdf.setFont("Courier-Bold", 9)
    pdf.drawString(MARGIN, y, "Total:")
    pdf.drawRightString(TICKET_WIDTH-MARGIN, y, f"${total:.2f}")
    y -= LINE_HEIGHT + 2

    # --- QR code centré ---
    qr_img = qrcode.make(reservation.qrcode_data)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_reader = ImageReader(qr_buffer)
    qr_size = 25 * mm
    pdf.drawImage(qr_reader, (TICKET_WIDTH-qr_size)/2, y-qr_size, qr_size, qr_size)
    y -= qr_size + 3

    # --- Footer ---
    pdf.setFont("Courier-Oblique", 6)
    pdf.drawCentredString(TICKET_WIDTH/2, y, "Merci pour votre commande !")
    y -= LINE_HEIGHT
    pdf.drawCentredString(TICKET_WIDTH/2, y, "Présentez le QR code à l'arrivée.")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"ticket_{reservation.id_reservation}.pdf",
        mimetype='application/pdf'
    )


# -----------------------------
# Recommander une commande
# -----------------------------
@reservation_public_bp.route('/recommander/<int:reservation_id>', methods=['POST'])
def recommander_commande(reservation_id):
    client_id = session.get('client_id')
    if not client_id:
        return jsonify({'success': False, 'message': 'Veuillez vous connecter.'})

    reservation = Reservation.query.get_or_404(reservation_id)
    items = reservation.items
    if not items:
        return jsonify({'success': False, 'message': 'Aucun plat à recommander.'})

    panier = session.get('panier', [])
    total_articles = 0

    for item in items:
        for p in panier:
            if p['id'] == item.plat_id:
                p['quantite'] += item.quantite
                break
        else:
            panier.append({
                'id': item.plat_id,
                'nom': item.plat.nom,
                'prix': float(item.prix_unitaire),
                'quantite': item.quantite
            })
        total_articles += item.quantite

    session['panier'] = panier
    session.modified = True

    return jsonify({'success': True, 'totalArticles': total_articles})

# -----------------------------
# Scanner : page interface
# -----------------------------
@reservation_public_bp.route('/scanner')
def scanner_page():
    return render_template("scanner.html")

# -----------------------------
# Scanner : API vérification QR
# -----------------------------
@reservation_public_bp.route('/scanner/verify', methods=['POST'])
def scanner_verify():
    try:
        data = request.get_json()
        qr_data = data.get("qr_data")

        if not qr_data:
            return jsonify({"success": False, "message": "QR Code invalide."})

        reservation = Reservation.query.filter_by(qrcode_data=qr_data).first()
        if not reservation:
            return jsonify({"success": False, "message": "Réservation introuvable."})

        if getattr(reservation, "status", "En attente") == "Servi":
            return jsonify({"success": False, "message": "Ce ticket a déjà été utilisé (client déjà servi)."})

        client = reservation.client
        items = [{
            "plat": item.plat.nom if item.plat else "Plat inconnu",
            "quantite": item.quantite,
            "prix": item.prix_unitaire
        } for item in reservation.items]

        total = sum(i["prix"] * i["quantite"] for i in items)

        return jsonify({
            "success": True,
            "reservation_id": reservation.id_reservation,
            "client": {
                "nom": client.nom,
                "email": client.email,
                "tel": client.telephone
            },
            "status": getattr(reservation, "status", "En attente"),
            "items": items,
            "total": total
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# -----------------------------
# Marquer une réservation comme servie
# -----------------------------
@reservation_public_bp.route('/scanner/serve/<int:reservation_id>', methods=['POST'])
def scanner_serve(reservation_id):
    try:
        reservation = Reservation.query.get_or_404(reservation_id)

        if getattr(reservation, "status", "En attente") == "Servi":
            return jsonify({"success": False, "message": "Ce client a déjà été servi."})

        reservation.status = "Servi"
        db.session.commit()
        return jsonify({"success": True, "message": "Client servi avec succès."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

# -----------------------------
# Clients servis
# -----------------------------
@reservation_public_bp.route('/clients-servis')
def clients_servis():
    clients_query = (
        Client.query
        .join(Reservation)
        .filter(Reservation.status == "Servi")
        .order_by(Client.nom.asc())
        .all()
    )

    clients = []
    today = date.today()

    for client in clients_query:
        served_reservations = [r for r in client.reservations if getattr(r, 'status', '') == 'Servi']
        total_served = len(served_reservations)
        last_reservation = max(served_reservations, key=lambda r: r.date_reservation, default=None)
        
        clients.append({
            'id_client': client.id_client,
            'nom': client.nom,
            'email': client.email,
            'telephone': client.telephone,
            'total_served': total_served,
            'last_reservation': last_reservation,
        })

    return render_template(
        'clients/clients_servis.html',
        clients=clients,
        today=today
    )
    
@reservation_public_bp.route('/liste_reservations')
def liste_reservations():
    search = request.args.get('search', '')

    # Récupérer toutes les réservations ou filtrer selon search
    if search:
        reservations = ReservationItem.query.join(Plat).filter(Plat.nom.ilike(f"%{search}%")).all()
    else:
        reservations = ReservationItem.query.all()

    # Calculer le total par plat
    plats_sommes = {}
    for item in reservations:
        nom_plat = item.plat.nom if item.plat else "Plat inconnu"
        prix = item.prix_unitaire if item.prix_unitaire is not None else (item.plat.prix if item.plat else 0)
        if nom_plat in plats_sommes:
            plats_sommes[nom_plat]['quantite'] += item.quantite
            plats_sommes[nom_plat]['total'] += prix * item.quantite
        else:
            plats_sommes[nom_plat] = {'quantite': item.quantite, 'total': prix * item.quantite}

    return render_template(
        'liste_reservations.html',
        reservations=reservations,
        search=search,
        plats_sommes=plats_sommes  
    )


@reservation_public_bp.route('/reserver_table', methods=['POST'])
def reserver_table():
    client_id = session.get('client_id')
    if not client_id:
        flash("Vous devez être connecté pour réserver.", "warning")
        return redirect(url_for('plats_public.afficher_menu'))

    try:
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        email = request.form.get('email', '').strip()
        tel = request.form.get('tel', '').strip()
        date_str = request.form.get('date', '').strip()
        heure_str = request.form.get('heure', '').strip()
        personnes = request.form.get('personnes', '').strip()

        if not all([nom, email, tel, date_str, heure_str, personnes]):
            flash("Veuillez remplir tous les champs obligatoires.", "danger")
            return redirect(url_for('reservation_public.mon_panier'))

        date_res = datetime.strptime(date_str, "%Y-%m-%d").date()
        heure_res = datetime.strptime(heure_str, "%H:%M").time()

        # Vérifier disponibilité max 10 tables
        existing = Reservation.query.filter_by(date_reservation=date_res, heure_reservation=heure_res).count()
        if existing >= 10:
            flash("Désolé, aucune table disponible à cette heure.", "warning")
            return redirect(url_for('reservation_public.mon_panier'))

        # Création réservation
        new_res = Reservation(
            nom_client=nom,
            prenom_client=prenom,
            email_client=email,
            telephone=tel,
            date_reservation=date_res,
            heure_reservation=heure_res,
            nombre_personnes=int(personnes),
            status="En attente",
            qrcode_data=f"{tel}_{datetime.now().timestamp()}"
        )
        db.session.add(new_res)
        db.session.commit()

        # Générer PDF + envoyer email
        pdf_bytes = generer_pdf_ticket(new_res)
        envoyer_ticket_email(new_res, pdf_bytes)

        flash("Votre réservation a été enregistrée avec succès ! Un ticket vous a été envoyé par email.", "success")
        return redirect(url_for('reservation_public.ticket_view', reservation_id=new_res.id_reservation))

    except Exception as e:
        db.session.rollback()
        flash("Erreur lors de la réservation. Veuillez réessayer.", "danger")
        return redirect(url_for('reservation_public.mon_panier'))


# ---------------------------
# Route pour afficher le ticket en ligne
# ---------------------------
@reservation_public_bp.route('/ticket/<int:reservation_id>')
def ticket_view(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    qr_base64 = generer_qr_base64(reservation.qrcode_data)
    return render_template('public/ticket_table.html', reservation=reservation, qr_base64=qr_base64)


# ---------------------------
# Route pour télécharger le PDF du ticket
# ---------------------------
@reservation_public_bp.route('/ticket_pdf/<int:reservation_id>')
def ticket_pdf_download(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    pdf_bytes = generer_pdf_ticket(reservation)
    return send_file(
        io.BytesIO(pdf_bytes),
        download_name=f"Ticket_{reservation.id_reservation}.pdf",
        as_attachment=True
    )


# ---------------------------
# Générer QR code base64
# ---------------------------
def generer_qr_base64(data):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return f"data:image/png;base64,{base64.b64encode(buffer.read()).decode()}"


# ---------------------------
# Générer PDF ticket
# ---------------------------
def generer_pdf_ticket(reservation):
    qr_base64 = generer_qr_base64(reservation.qrcode_data)
    html = render_template('public/ticket_table.html', reservation=reservation, qr_base64=qr_base64)
    return HTML(string=html).write_pdf()


# ---------------------------
# Envoyer ticket par email
# ---------------------------
def envoyer_ticket_email(reservation, pdf_bytes):
    msg = Message(
        subject=f"🎟️ Votre ticket de réservation - Table {reservation.id_reservation}",
        recipients=[reservation.email_client]
    )
    msg.body = f"""
Bonjour {reservation.nom_client},

Merci pour votre réservation de table au restaurant 🍽️.
Voici les détails :

📅 Date : {reservation.date_reservation}
🕓 Heure : {reservation.heure_reservation}
👥 Nombre de personnes : {reservation.nombre_personnes}

Vous trouverez ci-joint votre ticket avec QR code.

À très bientôt !
"""
    msg.attach(
        filename=f"ticket_{reservation.id_reservation}.pdf",
        content_type='application/pdf',
        data=pdf_bytes
    )
    mail.send(msg)