# database.py
# This file does ONE job only:
# It creates the database connection for our entire project
# Think of it like: "opening the shop's record book"

from flask_sqlalchemy import SQLAlchemy
import os

# This 'db' object is our database
# We will import this in ALL other files
db = SQLAlchemy()

def init_db(app):
    # Find the exact location of our 'data' folder
    # No matter where you run the project from
    BASE_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..') 
    )
    
    # Tell Flask where the database file lives
    DB_PATH = os.path.join(BASE_DIR, 'data', 'shop.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
    
    # This turns off a feature we don't need
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Connect the database to our Flask app
    db.init_app(app)
    
    # Create all tables automatically
    with app.app_context():
        db.create_all()
        print("✅ Database connected and tables created!")