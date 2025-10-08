# models.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db  # ⚠️ Assure-toi que extensions.py contient db = SQLAlchemy()

# -------------------------------
# Table des catégories
# -------------------------------
class Categorie(db.Model):
    __tablename__ = 'categorie'
    categorie_id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False, unique=True)

    # Relation vers les plats
    plats = db.relationship(
        'Plat',
        back_populates='categorie',
        cascade='all, delete-orphan',
        passive_deletes=True
    )

    def __repr__(self):
        return f"<Categorie {self.nom}>"


# -------------------------------
# Table des clients
# -------------------------------
class Client(db.Model):
    __tablename__ = 'clients'
    id_client = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100))
    email = db.Column(db.String(100), nullable=False, unique=True)
    telephone = db.Column(db.String(20))
    mot_de_passe = db.Column(db.String(200), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)

    reservations = db.relationship(
        'Reservation',
        back_populates='client',
        cascade='all, delete-orphan'
    )
    avis = db.relationship('Avis', back_populates='client', cascade='all, delete-orphan')

    def set_password(self, password):
        self.mot_de_passe = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.mot_de_passe, password)

    def __repr__(self):
        return f"<Client {self.nom} {self.prenom} - {self.email}>"


# -------------------------------
# Table des plats
# -------------------------------
class Plat(db.Model):
    __tablename__ = 'plats'
    id_plat = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    prix = db.Column(db.Numeric(7, 2), nullable=False)
    image_url = db.Column(db.Text)

    categorie_id = db.Column(
        db.Integer,
        db.ForeignKey('categorie.categorie_id', ondelete='SET NULL'),
        nullable=True
    )
    categorie = db.relationship('Categorie', back_populates='plats')

    reservation_items = db.relationship(
        'ReservationItem',
        back_populates='plat',
        cascade='all, delete-orphan'
    )
    avis = db.relationship('Avis', back_populates='plat', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Plat {self.nom} ({float(self.prix)}$)>"


# -------------------------------
# Table des réservations
# -------------------------------
class Reservation(db.Model):
    __tablename__ = 'reservations'
    id_reservation = db.Column(db.Integer, primary_key=True)
    id_client = db.Column(
        db.Integer,
        db.ForeignKey('clients.id_client', ondelete='CASCADE'),
        nullable=True
    )

    nom_client = db.Column(db.String(100), nullable=True)
    prenom_client = db.Column(db.String(100), nullable=True)
    email_client = db.Column(db.String(100), nullable=True)
    telephone = db.Column(db.String(20), nullable=True)

    date_reservation = db.Column(db.Date, nullable=False)
    heure_reservation = db.Column(db.Time, nullable=False)
    nombre_personnes = db.Column(db.Integer, default=1, nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='En attente')
    qrcode_data = db.Column(db.String(255))

    client = db.relationship('Client', back_populates='reservations')
    items = db.relationship(
        'ReservationItem',
        back_populates='reservation',
        cascade='all, delete-orphan'
    )

    @property
    def total(self):
        return float(sum(item.total for item in self.items))

    def __repr__(self):
        nom_affiche = self.nom_client or (self.client.nom if self.client else "Inconnu")
        return f"<Reservation {self.id_reservation} - Client {nom_affiche}>"


# -------------------------------
# Table des détails de réservation
# -------------------------------
class ReservationItem(db.Model):
    __tablename__ = 'reservation_items'
    id_item = db.Column(db.Integer, primary_key=True)
    id_reservation = db.Column(
        db.Integer,
        db.ForeignKey('reservations.id_reservation', ondelete='CASCADE'),
        nullable=False
    )
    plat_id = db.Column(
        db.Integer,
        db.ForeignKey('plats.id_plat', ondelete='CASCADE'),
        nullable=False
    )
    quantite = db.Column(db.Integer, default=1, nullable=False)
    prix_unitaire = db.Column(db.Numeric(7, 2), nullable=False)

    __table_args__ = (
        db.CheckConstraint('quantite > 0', name='check_quantite_positive'),
    )

    reservation = db.relationship('Reservation', back_populates='items')
    plat = db.relationship('Plat', back_populates='reservation_items')

    @property
    def total(self):
        return float(self.prix_unitaire) * self.quantite

    def __repr__(self):
        return f"<ReservationItem Reservation={self.id_reservation}, Plat={self.plat_id}, Quantite={self.quantite}>"


# -------------------------------
# Table des contacts
# -------------------------------
class Contact(db.Model):
    __tablename__ = 'contact'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    agent = db.Column(db.String(50))
    date_envoi = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------------------
# Table des avis
# -------------------------------
class Avis(db.Model):
    __tablename__ = 'avis'
    id_avis = db.Column(db.Integer, primary_key=True)
    id_plat = db.Column(
        db.Integer,
        db.ForeignKey('plats.id_plat', ondelete='CASCADE'),
        nullable=False
    )
    id_client = db.Column(
        db.Integer,
        db.ForeignKey('clients.id_client', ondelete='CASCADE'),
        nullable=False
    )
    note = db.Column(db.Integer, nullable=False)
    commentaire = db.Column(db.Text)
    date_avis = db.Column(db.DateTime, default=datetime.utcnow)

    plat = db.relationship('Plat', back_populates='avis')
    client = db.relationship('Client', back_populates='avis')

    def __repr__(self):
        return f"<Avis Client={self.id_client}, Plat={self.id_plat}, Note={self.note}>"
