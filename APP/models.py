from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Aquarium(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    size = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200))
    fishes = db.relationship('Fish', backref='aquarium', lazy=True, cascade="all, delete-orphan")
    maintenances = db.relationship('Maintenance', backref='aquarium', lazy=True, cascade="all, delete-orphan")

class Fish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    species = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    aquarium_id = db.Column(db.Integer, db.ForeignKey('aquarium.id'), nullable=False)

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    task = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text)
    aquarium_id = db.Column(db.Integer, db.ForeignKey('aquarium.id'), nullable=False)
