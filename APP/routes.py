from flask import Blueprint, render_template, request, redirect, url_for, flash
from .models import db, Aquarium, Fish, Maintenance
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
def index():
    aquariums = Aquarium.query.all()
    return render_template('index.html', aquariums=aquariums)

# Ajoutez ici toutes vos autres routes...
