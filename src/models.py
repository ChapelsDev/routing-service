"""
Modelos ORM para PostgreSQL
— mantém-se Flask-SQLAlchemy, mas tiramos partido dos tipos nativos do dialecto
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from datetime import datetime
import uuid, secrets

db = SQLAlchemy()          # inicializas no teu create_app()


# ---------- ApiKey ----------------------------------------
class ApiKey(db.Model):
    __tablename__ = "api_keys"

    id         = db.Column(db.Integer, primary_key=True)          # SERIAL
    key        = db.Column(db.String(64), unique=True,
                           nullable=False,
                           default=lambda: secrets.token_urlsafe(32))
    owner      = db.Column(db.String(120))
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())

    def __repr__(self):
        return f"<ApiKey {self.key}>"


# ---------- Route -----------------------------------------
class Route(db.Model):
    __tablename__ = "routes"

    id          = db.Column(UUID(as_uuid=True), primary_key=True,
                            default=uuid.uuid4)                  # UUID nativo
    user_id     = db.Column(db.String(120))
    origin      = db.Column(db.Text, nullable=False)
    destination = db.Column(db.Text)
    preferences = db.Column(db.Text)
    details     = db.Column(db.Text, nullable=False,
                            server_default="Route created")
    created_at  = db.Column(db.DateTime(timezone=True),
                            server_default=func.now())

    # métricas agregadas
    distance_m  = db.Column(db.Float, default=0.0)
    duration_s  = db.Column(db.Float, default=0.0)

    # geometria/styling (ex.: LineString do OSRM) guardada como JSONB
    geometry    = db.Column(JSONB)

    # relação 1-N → RouteStep
    steps = db.relationship(
        "RouteStep",
        backref="route",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


# ---------- RouteStep -------------------------------------
class RouteStep(db.Model):
    __tablename__ = "route_steps"

    id         = db.Column(db.Integer, primary_key=True)          # SERIAL
    route_id   = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("routes.id", ondelete="CASCADE"),
        nullable=False
    )
    step_order = db.Column(db.Integer, default=1)
    location   = db.Column(db.String(255))
    notes      = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
