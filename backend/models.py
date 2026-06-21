# models.py
# This file defines our database TABLES
# Each class = one table in the database
# Think of each class as a "form template" for the shop

from database import db
from datetime import datetime
import bcrypt

# ─────────────────────────────────────────
# TABLE 1: Products
# Stores all products available in the shop
# Example row: Rice, Grocery, buy=180, sell=220, stock=50
# ─────────────────────────────────────────
class Product(db.Model):
    __tablename__ = 'products'

    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(100), nullable=False)
    category       = db.Column(db.String(50), default='General')
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price  = db.Column(db.Float, nullable=False)
    current_stock  = db.Column(db.Integer, default=0)
    reorder_level  = db.Column(db.Integer, default=10)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    # Links this table to DailySale and StockUpdate tables
    sales         = db.relationship('DailySale', backref='product', lazy=True)
    stock_updates = db.relationship('StockUpdate', backref='product', lazy=True)

    def profit_per_unit(self):
        # How much profit do we make selling ONE unit?
        return self.selling_price - self.purchase_price

    def to_dict(self):
        # Converts this object to a dictionary
        # So we can send it as JSON to the frontend
        return {
            'id'            : self.id,
            'name'          : self.name,
            'category'      : self.category,
            'purchase_price': self.purchase_price,
            'selling_price' : self.selling_price,
            'current_stock' : self.current_stock,
            'reorder_level' : self.reorder_level,
            'profit_per_unit': self.profit_per_unit()
        }


# ─────────────────────────────────────────
# TABLE 2: Daily Sales
# Records every sale made in the shop
# Example row: Sold 5 Rice packets on 2024-01-15 for Rs.220 each
# ─────────────────────────────────────────
class DailySale(db.Model):
    __tablename__ = 'daily_sales'

    id            = db.Column(db.Integer, primary_key=True)
    product_id    = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=False)
    sale_price    = db.Column(db.Float, nullable=False)
    revenue       = db.Column(db.Float)
    date          = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    notes         = db.Column(db.String(200), default='')

    def calculate_revenue(self):
        # Revenue = quantity sold × price per unit
        return self.quantity_sold * self.sale_price

    def to_dict(self):
        return {
            'id'           : self.id,
            'product_id'   : self.product_id,
            'product_name' : self.product.name if self.product else None,
            'quantity_sold': self.quantity_sold,
            'sale_price'   : self.sale_price,
            'revenue'      : self.revenue,
            'date'         : self.date.strftime('%Y-%m-%d'),
            'notes'        : self.notes
        }


# ─────────────────────────────────────────
# TABLE 3: Expenses
# Tracks all shop expenses
# Example row: Rent, Rs.5000, 2024-01-01
# ─────────────────────────────────────────
class Expense(db.Model):
    __tablename__ = 'expenses'

    id          = db.Column(db.Integer, primary_key=True)
    category    = db.Column(db.String(50), nullable=False)
    amount      = db.Column(db.Float, nullable=False)
    date        = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(200), default='')

    def to_dict(self):
        return {
            'id'         : self.id,
            'category'   : self.category,
            'amount'     : self.amount,
            'date'       : self.date.strftime('%Y-%m-%d'),
            'description': self.description
        }


# ─────────────────────────────────────────
# TABLE 4: Stock Updates
# Records when new stock arrives from supplier
# Example row: Added 100 Rice packets on 2024-01-10
# ─────────────────────────────────────────
class StockUpdate(db.Model):
    __tablename__ = 'stock_updates'

    id             = db.Column(db.Integer, primary_key=True)
    product_id     = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity_added = db.Column(db.Integer, nullable=False)
    supplier_price = db.Column(db.Float)
    date           = db.Column(db.Date, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id'            : self.id,
            'product_id'    : self.product_id,
            'product_name'  : self.product.name if self.product else None,
            'quantity_added': self.quantity_added,
            'supplier_price': self.supplier_price,
            'date'          : self.date.strftime('%Y-%m-%d')
        }
    # ─────────────────────────────────────────
# Bill Model — One row per customer bill
# ─────────────────────────────────────────
class Bill(db.Model):
    __tablename__ = 'bills'

    id            = db.Column(db.Integer, primary_key=True)
    bill_number   = db.Column(db.String(20), unique=True, nullable=False)
    total_amount  = db.Column(db.Float, default=0)
    total_cost    = db.Column(db.Float, default=0)
    total_profit  = db.Column(db.Float, default=0)
    date          = db.Column(db.Date, nullable=False)
    notes         = db.Column(db.String(200), nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # One bill has many items
    items = db.relationship(
        'BillItem',
        backref='bill',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def to_dict(self):
        return {
            'id'           : self.id,
            'bill_number'  : self.bill_number,
            'total_amount' : self.total_amount,
            'total_cost'   : self.total_cost,
            'total_profit' : self.total_profit,
            'date'         : str(self.date),
            'notes'        : self.notes,
            'created_at'   : str(self.created_at),
            'items'        : [item.to_dict() for item in self.items]
        }


# ─────────────────────────────────────────
# BillItem Model — Each product in a bill
# ─────────────────────────────────────────
class BillItem(db.Model):
    __tablename__ = 'bill_items'

    id          = db.Column(db.Integer, primary_key=True)
    bill_id     = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False)
    product_id  = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity    = db.Column(db.Integer, nullable=False)
    unit_price  = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    unit_cost   = db.Column(db.Float, nullable=False)

    # Link to product
    product = db.relationship('Product', backref='bill_items', lazy=True)

    def to_dict(self):
        return {
            'id'          : self.id,
            'bill_id'     : self.bill_id,
            'product_id'  : self.product_id,
            'product_name': self.product.name,
            'quantity'    : self.quantity,
            'unit_price'  : self.unit_price,
            'total_price' : self.total_price,
            'unit_cost'   : self.unit_cost,
            'profit'      : round(
                (self.unit_price - self.unit_cost) * self.quantity, 2
            )
        }
    # ─────────────────────────────────────────
# User Model — For login and authentication
# ─────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name     = db.Column(db.String(100), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default='staff')
                    # Values: 'owner', 'manager', 'staff'
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login    = db.Column(db.DateTime, nullable=True)

    def set_password(self, plain_password):
        """Hash and store password securely"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(
            plain_password.encode('utf-8'), salt
        ).decode('utf-8')

    def check_password(self, plain_password):
        """Check if entered password matches stored hash"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def to_dict(self):
        return {
            'id'        : self.id,
            'username'  : self.username,
            'full_name' : self.full_name,
            'role'      : self.role,
            'is_active' : self.is_active,
            'created_at': str(self.created_at),
            'last_login': str(self.last_login) if self.last_login else None
        }