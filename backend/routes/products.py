# routes/products.py
# This file handles everything related to PRODUCTS
# Think of it as the "product register" of our shop
# It has 4 jobs: Get, Add, Update, Delete products

from flask import Blueprint, request, jsonify
from database import db
from models import Product

# Blueprint = a mini-app that handles only product routes
products_bp = Blueprint('products', __name__)


# ─────────────────────────────────────────
# JOB 1: GET all products
# URL: GET http://localhost:5000/api/products
# ─────────────────────────────────────────
@products_bp.route('/api/products', methods=['GET'])
def get_products():
    """Returns the full list of products in the shop"""
    products = Product.query.all()
    return jsonify({
        'success': True,
        'data'   : [p.to_dict() for p in products],
        'count'  : len(products)
    })


# ─────────────────────────────────────────
# JOB 2: ADD a new product
# URL: POST http://localhost:5000/api/products
# ─────────────────────────────────────────
@products_bp.route('/api/products', methods=['POST'])
def add_product():
    """Adds a new product to the shop"""
    data = request.get_json()

    # Check that required fields are present
    required_fields = ['name', 'purchase_price', 'selling_price']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error'  : f'Missing field: {field}'
            }), 400

    # Create the new product object
    product = Product(
        name           = data['name'],
        category       = data.get('category', 'General'),
        purchase_price = float(data['purchase_price']),
        selling_price  = float(data['selling_price']),
        current_stock  = int(data.get('current_stock', 0)),
        reorder_level  = int(data.get('reorder_level', 10))
    )

    # Save to database
    db.session.add(product)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Product "{product.name}" added successfully!',
        'data'   : product.to_dict()
    }), 201


# ─────────────────────────────────────────
# JOB 3: UPDATE an existing product
# URL: PUT http://localhost:5000/api/products/1
# ─────────────────────────────────────────
@products_bp.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Updates an existing product by its ID"""
    product = Product.query.get_or_404(product_id)
    data    = request.get_json()

    # Update only the fields that were sent
    updatable_fields = [
        'name', 'category', 'purchase_price',
        'selling_price', 'current_stock', 'reorder_level'
    ]
    for field in updatable_fields:
        if field in data:
            setattr(product, field, data[field])

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Product updated successfully!',
        'data'   : product.to_dict()
    })


# ─────────────────────────────────────────
# JOB 4: DELETE a product
# URL: DELETE http://localhost:5000/api/products/1
# ─────────────────────────────────────────
@products_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Deletes a product by its ID"""
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Product "{product.name}" deleted!'
    })