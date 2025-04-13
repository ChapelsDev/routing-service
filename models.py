# models.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets


db = SQLAlchemy()


class ApiKey(db.Model):
    __tablename__ = "api_keys"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String, unique=True, nullable=False)
    owner = db.Column(db.String, nullable=True)  # e.g. to identify who this key belongs to
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ApiKey {self.key}>"

class Route(db.Model):
    __tablename__ = "routes"

    id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.String, nullable=True)
    origin = db.Column(db.Text, nullable=False)
    destination = db.Column(db.Text, nullable=True)
    preferences = db.Column(db.Text, nullable=True)
    details = db.Column(db.Text, default="Route created")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # NEW COLUMNS
    distance_m = db.Column(db.Float, default=0.0)    # total route distance in meters
    duration_s = db.Column(db.Float, default=0.0)    # total route duration in seconds
    geometry = db.Column(db.Text, nullable=True)     # store route geometry (LineString) as JSON

    steps = db.relationship("RouteStep", backref="route", cascade="all, delete")

class RouteStep(db.Model):
    __tablename__ = "route_steps"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    route_id = db.Column(db.String, db.ForeignKey("routes.id"), nullable=False)
    step_order = db.Column(db.Integer, default=1)
    location = db.Column(db.String, nullable=True)
    notes = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
