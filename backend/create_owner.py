"""
Run this file ONCE to create the first owner account.
After running, delete this file for security.

Usage:
  cd backend
  python create_owner.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from database import db
from models import User

# ── Change these before running! ──
OWNER_USERNAME  = "admin"
OWNER_PASSWORD  = "shop@2026"
OWNER_FULLNAME  = "Muhammad Faizan"
# ──────────────────────────────────

app = create_app()

with app.app_context():

    # Create tables if not exist
    db.create_all()

    # Check if already exists
    existing = User.query.filter_by(
        username=OWNER_USERNAME
    ).first()

    if existing:
        print(f"⚠️  User '{OWNER_USERNAME}' already exists!")
        print("    Delete from DB and re-run if needed.")
    else:
        owner = User(
            username  = OWNER_USERNAME,
            full_name = OWNER_FULLNAME,
            role      = 'owner'
        )
        owner.set_password(OWNER_PASSWORD)
        db.session.add(owner)
        db.session.commit()

        print("✅ Owner account created successfully!")
        print(f"   Username : {OWNER_USERNAME}")
        print(f"   Password : {OWNER_PASSWORD}")
        print(f"   Role     : owner")
        print("")
        print("⚠️  Please delete this file now for security!")