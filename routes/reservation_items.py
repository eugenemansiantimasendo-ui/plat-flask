from flask import Blueprint, render_template, request, jsonify
from models import db, ReservationItem, Reservation, Client, Plat
from sqlalchemy import or_, func

reservation_items_bp = Blueprint(
    'reservation_items',
    __name__,
    template_folder='templates/reservation_items'
)

# -----------------------------
# Liste des plats réservés
# -----------------------------
@reservation_items_bp.route('/', methods=['GET'])
def list_reservation_items():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    search = request.args.get('search', '').strip()

    query = (
        ReservationItem.query
        .join(ReservationItem.reservation)
        .join(ReservationItem.plat)
        .join(Reservation.client)
        .order_by(Reservation.date_reservation.desc())
    )

    if search:
        query = query.filter(
            or_(
                Client.nom.ilike(f"%{search}%"),
                Client.email.ilike(f"%{search}%"),
                Client.telephone.ilike(f"%{search}%"),
                Plat.nom.ilike(f"%{search}%")
            )
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = pagination.items

    # Totaux
    total_qte_query = db.session.query(func.sum(ReservationItem.quantite)) \
        .join(ReservationItem.reservation) \
        .join(ReservationItem.plat) \
        .join(Reservation.client)
    if search:
        total_qte_query = total_qte_query.filter(
            or_(
                Client.nom.ilike(f"%{search}%"),
                Client.email.ilike(f"%{search}%"),
                Client.telephone.ilike(f"%{search}%"),
                Plat.nom.ilike(f"%{search}%")
            )
        )
    total_qte = total_qte_query.scalar() or 0

    montant_total_query = db.session.query(func.sum(ReservationItem.quantite * Plat.prix)) \
        .join(ReservationItem.reservation) \
        .join(ReservationItem.plat) \
        .join(Reservation.client)
    if search:
        montant_total_query = montant_total_query.filter(
            or_(
                Client.nom.ilike(f"%{search}%"),
                Client.email.ilike(f"%{search}%"),
                Client.telephone.ilike(f"%{search}%"),
                Plat.nom.ilike(f"%{search}%")
            )
        )
    montant_total = float(montant_total_query.scalar() or 0.0)

    # Clients uniques
    clients_query = db.session.query(Client.id_client) \
        .distinct() \
        .join(Reservation) \
        .join(ReservationItem, ReservationItem.id_reservation == Reservation.id_reservation) \
        .join(Plat)
    if search:
        clients_query = clients_query.filter(
            or_(
                Client.nom.ilike(f"%{search}%"),
                Client.email.ilike(f"%{search}%"),
                Client.telephone.ilike(f"%{search}%"),
                Plat.nom.ilike(f"%{search}%")
            )
        )
    clients = clients_query.count()

    return render_template(
        'reservation_items/liste_plats_reserves.html',
        items=items,
        pagination=pagination,
        search=search,
        total_qte=total_qte,
        montant_total=montant_total,
        clients=clients
    )

# -----------------------------
# Historique d’un client (AJAX)
# -----------------------------
@reservation_items_bp.route('/client_history/<int:client_id>', methods=['GET'])
def client_history(client_id):
    client = Client.query.get_or_404(client_id)

    items_client = (
        db.session.query(ReservationItem)
        .join(ReservationItem.reservation)
        .join(ReservationItem.plat)
        .filter(Reservation.id_client == client.id_client)
        .order_by(Reservation.date_reservation.desc(), Reservation.heure_reservation.desc())
        .all()
    )

    history = []
    total_general = 0.0

    for item in items_client:
        quantite = float(item.quantite or 0)
        prix_unitaire = float(item.plat.prix or 0)
        total = quantite * prix_unitaire
        total_general += total

        history.append({
            "plat": item.plat.nom,
            "quantite": quantite,
            "prix_unitaire": prix_unitaire,
            "total": total,
            "date": item.reservation.date_reservation.strftime('%d/%m/%Y'),
            "heure": item.reservation.heure_reservation.strftime('%H:%M'),
            "status": item.reservation.status
        })

    # Ajouter le total cumulé comme dernier élément
    history.append({
        "plat": "TOTAL",
        "quantite": "",
        "prix_unitaire": "",
        "total": total_general,
        "date": "",
        "heure": "",
        "status": ""
    })

    return jsonify(history)
