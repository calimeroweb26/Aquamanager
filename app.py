from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aquariums.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SECRET_KEY'] = 'votre_cle_secrete_ici'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 Mo max

# Création des dossiers nécessaires
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Modèles de base de données
class Aquarium(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Float, nullable=False)  # Taille en litres
    description = db.Column(db.Text)
    water_changes = db.relationship('WaterChange', backref='aquarium', cascade='all, delete-orphan')
    photos = db.relationship('Photo', backref='aquarium', cascade='all, delete-orphan')

class WaterChange(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aquarium_id = db.Column(db.Integer, db.ForeignKey('aquarium.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    volume = db.Column(db.Float, nullable=False)  # Volume changé en litres
    notes = db.Column(db.Text)
    next_change = db.Column(db.Date)

    def calculate_next_change(self):
        """Calcule la date du prochain changement (tous les 7 jours)"""
        return self.date + timedelta(days=7)

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    aquarium_id = db.Column(db.Integer, db.ForeignKey('aquarium.id'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

# Fonctions utilitaires
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Routes principales
@app.route('/')
def index():
    aquariums = Aquarium.query.all()
    return render_template('index.html', aquariums=aquariums)

@app.route('/add', methods=['GET', 'POST'])
def add_aquarium():
    if request.method == 'POST':
        name = request.form['name']
        size = float(request.form['size'])
        description = request.form['description']

        new_aquarium = Aquarium(name=name, size=size, description=description)
        db.session.add(new_aquarium)
        db.session.commit()

        flash('Aquarium ajouté avec succès!', 'success')
        return redirect(url_for('index'))

    return render_template('add_aquarium.html')

@app.route('/aquarium/<int:id>')
def aquarium_detail(id):
    aquarium = Aquarium.query.get_or_404(id)
    photos = Photo.query.filter_by(aquarium_id=id).all()
    return render_template('aquarium.html', aquarium=aquarium, photos=photos)

@app.route('/aquarium/<int:id>/add_photo', methods=['POST'])
def add_photo(id):
    aquarium = Aquarium.query.get_or_404(id)

    if 'photo' not in request.files:
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('aquarium_detail', id=id))

    file = request.files['photo']
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'danger')
        return redirect(url_for('aquarium_detail', id=id))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_photo = Photo(filename=filename, aquarium_id=id)
        db.session.add(new_photo)
        db.session.commit()

        flash('Photo ajoutée avec succès!', 'success')
    else:
        flash('Type de fichier non autorisé', 'danger')

    return redirect(url_for('aquarium_detail', id=id))

@app.route('/aquarium/<int:id>/delete_photo/<int:photo_id>')
def delete_photo(id, photo_id):
    photo = Photo.query.get_or_404(photo_id)
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], photo.filename))
    db.session.delete(photo)
    db.session.commit()
    flash('Photo supprimée avec succès!', 'success')
    return redirect(url_for('aquarium_detail', id=id))

@app.route('/aquarium/<int:id>/add_water_change', methods=['POST'])
def add_water_change(id):
    aquarium = Aquarium.query.get_or_404(id)
    volume = float(request.form['volume'])
    notes = request.form['notes']

    new_change = WaterChange(
        aquarium_id=id,
        volume=volume,
        notes=notes
    )
    new_change.next_change = new_change.calculate_next_change()
    db.session.add(new_change)
    db.session.commit()

    flash('Changement d\'eau enregistré!', 'success')
    return redirect(url_for('water_change_history', id=id))

@app.route('/aquarium/<int:id>/water_changes')
def water_change_history(id):
    aquarium = Aquarium.query.get_or_404(id)
    changes = WaterChange.query.filter_by(aquarium_id=id).order_by(WaterChange.date.desc()).all()

    # Préparation des données pour le graphique
    dates = [change.date.strftime('%Y-%m-%d') for change in changes]
    volumes = [change.volume for change in changes]

    return render_template(
        'water_change_history.html',
        aquarium=aquarium,
        changes=changes,
        dates=dates,
        volumes=volumes
    )

@app.route('/aquarium/<int:id>/delete_water_change/<int:change_id>')
def delete_water_change(id, change_id):
    change = WaterChange.query.get_or_404(change_id)
    db.session.delete(change)
    db.session.commit()
    flash('Changement d\'eau supprimé!', 'success')
    return redirect(url_for('water_change_history', id=id))

@app.route('/delete_aquarium/<int:id>')
def delete_aquarium(id):
    aquarium = Aquarium.query.get_or_404(id)

    # Supprimer les photos associées
    for photo in aquarium.photos:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], photo.filename))

    db.session.delete(aquarium)
    db.session.commit()
    flash('Aquarium supprimé avec succès!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')
