from flask import Blueprint, render_template, request
from models import db, Categorie, Plat, Client, Reservation, ReservationItem
from sqlalchemy import func, extract, desc
import calendar
from datetime import datetime, timedelta

# ---------------------------
# Blueprint 'index'
# ---------------------------
index_bp = Blueprint('index', __name__, template_folder='../templates/dashboard')

# ---------------------------
# Dictionnaire des devises
# ---------------------------
DEVISES = {
    "USD": "$",
    "CDF": "FC",
    "CFA": "CFA",
    "EUR": "€"
}

@index_bp.route('/', endpoint='dashboard_index')
def index():
    # ---------------------------
    # Devise sélectionnée
    # ---------------------------
    devise = request.args.get("devise", "USD")
    symbole = DEVISES.get(devise, "$")

    # ---------------------------
    # Comptages généraux
    # ---------------------------
    nb_clients = Client.query.count()
    nb_plats = Plat.query.count()
    nb_categories = Categorie.query.count()
    nb_reservations = Reservation.query.count()
    nb_serv_items = ReservationItem.query.count()
    nb_clients_servis = Reservation.query.filter_by(status="Servi").count()

    # ---------------------------
    # Derniers clients et réservations
    # ---------------------------
    derniers_clients = Client.query.order_by(Client.date_creation.desc()).limit(5).all()
    dernieres_reservations = Reservation.query.order_by(Reservation.date_reservation.desc()).limit(5).all()

    # ---------------------------
    # Graphiques par mois
    # ---------------------------
    mois_labels = [calendar.month_name[i] for i in range(1, 13)]
    reservations_par_mois = [
        Reservation.query.filter(extract('month', Reservation.date_reservation) == m).count()
        for m in range(1, 13)
    ]

    # ---------------------------
    # Top / faibles plats
    # ---------------------------
    top_plats = (
        db.session.query(
            Plat.nom,
            func.sum(ReservationItem.quantite).label('total')
        )
        .join(ReservationItem, Plat.id_plat == ReservationItem.plat_id)
        .group_by(Plat.nom)
        .order_by(desc('total'))
        .limit(5)
        .all()
    )

    plats_faibles = (
        db.session.query(
            Plat.nom,
            func.coalesce(func.sum(ReservationItem.quantite), 0).label('total')
        )
        .outerjoin(ReservationItem, Plat.id_plat == ReservationItem.plat_id)
        .group_by(Plat.nom)
        .order_by('total')
        .limit(5)
        .all()
    )

    # ---------------------------
    # Catégories et top catégories
    # ---------------------------
    categories_query = (
        db.session.query(
            Categorie.nom,
            func.count(Plat.id_plat).label('total_plats')
        )
        .outerjoin(Plat, Categorie.categorie_id == Plat.categorie_id)
        .group_by(Categorie.nom)
        .all()
    )

    categories_labels = [c.nom for c in categories_query]
    plats_par_categorie = [c.total_plats for c in categories_query]

    top_categories = {
        'labels': categories_labels,
        'data': plats_par_categorie
    }

    categories_faibles = sorted(categories_query, key=lambda x: x.total_plats)[:5]

    # ---------------------------
    # Analyse du potentiel client
    # ---------------------------
    clients_stats = (
        db.session.query(
            Client.id_client,
            Client.nom,
            func.count(Reservation.id_reservation).label('nb_reservations'),
            func.coalesce(func.sum(Plat.prix * ReservationItem.quantite), 0).label('total_depense'),
            func.max(Reservation.date_reservation).label('derniere_reservation')
        )
        .join(Reservation, Reservation.id_client == Client.id_client)
        .join(ReservationItem, ReservationItem.id_reservation == Reservation.id_reservation)
        .join(Plat, Plat.id_plat == ReservationItem.plat_id)
        .group_by(Client.id_client)
        .order_by(desc('total_depense'))
        .limit(5)
        .all()
    )

    seuil_inactif = datetime.now() - timedelta(days=90)
    clients_inactifs = (
        db.session.query(
            Client.nom,
            func.count(Reservation.id_reservation).label("nb_reservations"),
            func.coalesce(func.sum(Plat.prix * ReservationItem.quantite), 0).label("total_depense"),
            func.max(Reservation.date_reservation).label("derniere_reservation")
        )
        .outerjoin(Reservation, Reservation.id_client == Client.id_client)
        .outerjoin(ReservationItem, ReservationItem.id_reservation == Reservation.id_reservation)
        .outerjoin(Plat, Plat.id_plat == ReservationItem.plat_id)
        .group_by(Client.id_client)
        .having(func.max(Reservation.date_reservation) < seuil_inactif)
        .order_by(func.max(Reservation.date_reservation).asc())
        .limit(5)
        .all()
    )

    clients_sans_reservation = (
        db.session.query(Client)
        .outerjoin(Reservation, Client.id_client == Reservation.id_client)
        .filter(Reservation.id_reservation == None)
        .limit(5)
        .all()
    )

    # ---------------------------
    # Rendu du template
    # ---------------------------
    return render_template(
    "dashboard/index.html",
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
    top_plats=top_plats,
    plats_faibles=plats_faibles,
    categories_faibles=categories_faibles,
    categories_labels=categories_labels,
    plats_par_categorie=plats_par_categorie,
    top_categories=top_categories,
    devise=devise,
    symbole=symbole,
    devises=DEVISES,
    clients_stats=clients_stats,
    clients_inactifs=clients_inactifs,
    clients_sans_reservation=clients_sans_reservation
    
    
)
