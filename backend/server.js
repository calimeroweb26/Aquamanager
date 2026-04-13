const express  = require('express');
const sqlite3  = require('sqlite3').verbose();
const multer   = require('multer');
const cors     = require('cors');
const path     = require('path');
const fs       = require('fs');
const { v4: uuidv4 } = require('uuid');

const app      = express();
const PORT     = 3000;
const DB_PATH  = '/opt/aquamanager/data/aquamanager.db';
const UPL_PATH = '/opt/aquamanager/uploads';

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use('/uploads', express.static(UPL_PATH));
app.use(express.static('/opt/aquamanager/frontend'));

const db = new sqlite3.Database(DB_PATH);

db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS aquariums (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, litrage REAL,
        description TEXT, last_change TEXT, interval INTEGER,
        next_date TEXT, created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )`);
    db.run(`CREATE TABLE IF NOT EXISTS photos (
        id TEXT PRIMARY KEY, aquarium_id TEXT NOT NULL,
        filename TEXT NOT NULL, original_name TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (aquarium_id) REFERENCES aquariums(id) ON DELETE CASCADE
    )`);
});

const storage = multer.diskStorage({
    destination: (req, file, cb) => cb(null, UPL_PATH),
    filename: (req, file, cb) => {
        const ext = path.extname(file.originalname).toLowerCase();
        cb(null, uuidv4() + ext);
    }
});
const upload = multer({
    storage,
    limits: { fileSize: 10 * 1024 * 1024 },
    fileFilter: (req, file, cb) => {
        const ok = /jpeg|jpg|png|gif|webp/.test(path.extname(file.originalname).toLowerCase());
        cb(null, ok);
    }
});

function calcNext(last, interval) {
    if (!last || !interval) return null;
    const d = new Date(last);
    d.setDate(d.getDate() + parseInt(interval));
    return d.toISOString().split('T')[0];
}

app.get('/api/aquariums', (req, res) => {
    db.all('SELECT * FROM aquariums ORDER BY next_date ASC', [], (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        if (!rows.length) return res.json([]);
        const ids = rows.map(r => "'" + r.id + "'").join(',');
        db.all('SELECT * FROM photos WHERE aquarium_id IN (' + ids + ') ORDER BY created_at ASC', [], (e2, photos) => {
            res.json(rows.map(r => ({
                ...r,
                photos: (photos||[]).filter(p => p.aquarium_id === r.id)
                    .map(p => ({ id: p.id, url: '/uploads/' + p.filename, name: p.original_name }))
            })));
        });
    });
});

app.get('/api/aquariums/:id', (req, res) => {
    db.get('SELECT * FROM aquariums WHERE id = ?', [req.params.id], (err, row) => {
        if (err) return res.status(500).json({ error: err.message });
        if (!row) return res.status(404).json({ error: 'Non trouve' });
        db.all('SELECT * FROM photos WHERE aquarium_id = ?', [req.params.id], (e2, photos) => {
            row.photos = (photos||[]).map(p => ({ id: p.id, url: '/uploads/' + p.filename, name: p.original_name }));
            res.json(row);
        });
    });
});

app.post('/api/aquariums', upload.array('photos', 20), (req, res) => {
    const { name, litrage, description, last_change, interval } = req.body;
    if (!name) return res.status(400).json({ error: 'Nom requis' });
    const id = uuidv4();
    const next_date = calcNext(last_change, interval);
    db.run(
        'INSERT INTO aquariums (id,name,litrage,description,last_change,interval,next_date) VALUES (?,?,?,?,?,?,?)',
        [id, name, litrage||null, description||null, last_change||null, interval||null, next_date],
        function(err) {
            if (err) return res.status(500).json({ error: err.message });
            const stmt = db.prepare('INSERT INTO photos (id,aquarium_id,filename,original_name) VALUES (?,?,?,?)');
            (req.files||[]).forEach(f => stmt.run(uuidv4(), id, f.filename, f.originalname));
            stmt.finalize();
            res.status(201).json({ id, message: 'Cree' });
        }
    );
});

app.put('/api/aquariums/:id', upload.array('photos', 20), (req, res) => {
    const { name, litrage, description, last_change, interval, existingPhotos } = req.body;
    const next_date = calcNext(last_change, interval);
    const keepIds = existingPhotos ? JSON.parse(existingPhotos) : null;
    if (keepIds !== null) {
        db.all('SELECT * FROM photos WHERE aquarium_id = ?', [req.params.id], (err, allPhotos) => {
            allPhotos.filter(p => !keepIds.includes(p.id)).forEach(p => {
                const fp = path.join(UPL_PATH, p.filename);
                if (fs.existsSync(fp)) fs.unlinkSync(fp);
                db.run('DELETE FROM photos WHERE id = ?', [p.id]);
            });
        });
    }
    db.run(
        "UPDATE aquariums SET name=?,litrage=?,description=?,last_change=?,interval=?,next_date=?,updated_at=datetime('now') WHERE id=?",
        [name, litrage||null, description||null, last_change||null, interval||null, next_date, req.params.id],
        function(err) {
            if (err) return res.status(500).json({ error: err.message });
            if (!this.changes) return res.status(404).json({ error: 'Non trouve' });
            const stmt = db.prepare('INSERT INTO photos (id,aquarium_id,filename,original_name) VALUES (?,?,?,?)');
            (req.files||[]).forEach(f => stmt.run(uuidv4(), req.params.id, f.filename, f.originalname));
            stmt.finalize();
            res.json({ message: 'Mis a jour' });
        }
    );
});

app.patch('/api/aquariums/:id/change', (req, res) => {
    const today = new Date().toISOString().split('T')[0];
    db.get('SELECT interval FROM aquariums WHERE id = ?', [req.params.id], (err, row) => {
        if (err || !row) return res.status(404).json({ error: 'Non trouve' });
        const next_date = calcNext(today, row.interval);
        db.run(
            "UPDATE aquariums SET last_change=?,next_date=?,updated_at=datetime('now') WHERE id=?",
            [today, next_date, req.params.id],
            (e2) => {
                if (e2) return res.status(500).json({ error: e2.message });
                res.json({ message: 'Changement enregistre', last_change: today, next_date });
            }
        );
    });
});

app.delete('/api/aquariums/:id', (req, res) => {
    db.all('SELECT filename FROM photos WHERE aquarium_id = ?', [req.params.id], (err, photos) => {
        (photos||[]).forEach(p => {
            const fp = path.join(UPL_PATH, p.filename);
            if (fs.existsSync(fp)) fs.unlinkSync(fp);
        });
        db.run('DELETE FROM photos WHERE aquarium_id = ?', [req.params.id]);
        db.run('DELETE FROM aquariums WHERE id = ?', [req.params.id], function(e2) {
            if (e2) return res.status(500).json({ error: e2.message });
            res.json({ message: 'Supprime' });
        });
    });
});

app.delete('/api/photos/:id', (req, res) => {
    db.get('SELECT filename FROM photos WHERE id = ?', [req.params.id], (err, row) => {
        if (err || !row) return res.status(404).json({ error: 'Non trouve' });
        const fp = path.join(UPL_PATH, row.filename);
        if (fs.existsSync(fp)) fs.unlinkSync(fp);
        db.run('DELETE FROM photos WHERE id = ?', [req.params.id], (e2) => {
            if (e2) return res.status(500).json({ error: e2.message });
            res.json({ message: 'Photo supprimee' });
        });
    });
});

app.get('*', (req, res) => res.sendFile('/opt/aquamanager/frontend/index.html'));
app.listen(PORT, '0.0.0.0', () => console.log('AquaManager port ' + PORT));
