from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
from database import init_db, get_db_connection
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Initialiser la base de données
init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Routes
@app.route('/')
def index():
    conn = get_db_connection()
    aquariums = conn.execute('SELECT * FROM aquariums').fetchall()
    conn.close()
    return render_template('index.html', aquariums=aquariums)

@app.route('/add_aquarium', methods=['GET', 'POST'])
def add_aquarium():
    if request.method == 'POST':
        name = request.form['name']
        volume = request.form['volume']
        description = request.form['description']

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO aquariums (name, volume, description) VALUES (?, ?, ?)',
            (name, volume, description)
        )
        conn.commit()
        conn.close()
        flash('Aquarium ajouté avec succès!', 'success')
        return redirect(url_for('index'))
    return render_template('add_aquarium.html')

@app.route('/aquarium/<int:aquarium_id>')
def aquarium_detail(aquarium_id):
    conn = get_db_connection()
    aquarium = conn.execute('SELECT * FROM aquariums WHERE id = ?', (aquarium_id,)).fetchone()
    water_changes = conn.execute('SELECT * FROM water_changes WHERE aquarium_id = ? ORDER BY date DESC', (aquarium_id,)).fetchall()
    population = conn.execute('SELECT * FROM population WHERE aquarium_id = ?', (aquarium_id,)).fetchall()
    photos = conn.execute('SELECT * FROM photos WHERE aquarium_id = ? ORDER BY upload_date DESC', (aquarium_id,)).fetchall()
    conn.close()
    return render_template('aquarium.html', aquarium=aquarium, water_changes=water_changes, population=population, photos=photos)

@app.route('/add_water_change/<int:aquarium_id>', methods=['GET', 'POST'])
def add_water_change(aquarium_id):
    if request.method == 'POST':
        date = request.form['date']
        volume_changed = request.form['volume_changed']
        notes = request.form['notes']

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO water_changes (aquarium_id, date, volume_changed, notes) VALUES (?, ?, ?, ?)',
            (aquarium_id, date, volume_changed, notes)
        )
        conn.commit()
        conn.close()
        flash('Changement d\'eau enregistré!', 'success')
        return redirect(url_for('aquarium_detail', aquarium_id=aquarium_id))
    return render_template('add_water_change.html', aquarium_id=aquarium_id)

@app.route('/add_population/<int:aquarium_id>', methods=['POST'])
def add_population(aquarium_id):
    species = request.form['species']
    quantity = request.form['quantity']
    notes = request.form['notes']

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO population (aquarium_id, species, quantity, notes) VALUES (?, ?, ?, ?)',
        (aquarium_id, species, quantity, notes)
    )
    conn.commit()
    conn.close()
    flash('Population ajoutée!', 'success')
    return redirect(url_for('aquarium_detail', aquarium_id=aquarium_id))

@app.route('/upload_photo/<int:aquarium_id>', methods=['POST'])
def upload_photo(aquarium_id):
    if 'photo' not in request.files:
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('aquarium_detail', aquarium_id=aquarium_id))

    file = request.files['photo']
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('aquarium_detail', aquarium_id=aquarium_id))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO photos (aquarium_id, filename) VALUES (?, ?)',
            (aquarium_id, filename)
        )
        conn.commit()
        conn.close()
        flash('Photo téléchargée avec succès!', 'success')
    else:
        flash('Format de fichier non autorisé', 'error')

    return redirect(url_for('aquarium_detail', aquarium_id=aquarium_id))

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)
