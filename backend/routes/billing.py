from flask import Blueprint, request, jsonify
from database import db
from models import Bill, BillItem, Product
from datetime import date, datetime

billing_bp = Blueprint('billing', __name__)

# ─────────────────────────────────────────
# Helper — Generate unique bill number
# Format: BILL-YYYYMMDD-001
# ─────────────────────────────────────────
def generate_bill_number():
    today     = date.today()
    today_str = today.strftime('%Y%m%d')
    prefix    = f"BILL-{today_str}-"

    # Count today's bills and increment
    today_bills = Bill.query.filter(
        Bill.date == today
    ).count()

    number = str(today_bills + 1).zfill(3)
    return f"{prefix}{number}"


# ─────────────────────────────────────────
# GET /api/billing/bills
# Returns all bills (today by default)
# ─────────────────────────────────────────
@billing_bp.route('/api/billing/bills', methods=['GET'])
def get_bills():
    try:
        period = request.args.get('period', 'today')
        today  = date.today()

        if period == 'today':
            bills = Bill.query.filter(
                Bill.date == today
            ).order_by(Bill.created_at.desc()).all()
        elif period == 'all':
            bills = Bill.query.order_by(
                Bill.created_at.desc()
            ).limit(50).all()
        else:
            bills = Bill.query.filter(
                Bill.date == today
            ).order_by(Bill.created_at.desc()).all()

        # Today's summary
        today_bills   = Bill.query.filter(Bill.date == today).all()
        today_revenue = sum(b.total_amount for b in today_bills)
        today_profit  = sum(b.total_profit for b in today_bills)

        return jsonify({
            'success': True,
            'data'   : [b.to_dict() for b in bills],
            'summary': {
                'total_bills'  : len(today_bills),
                'total_revenue': round(today_revenue, 2),
                'total_profit' : round(today_profit, 2),
            }
        })
    except Exception as e:
        return jsonify({ 'success': False, 'error': str(e) }), 500


# ─────────────────────────────────────────
# GET /api/billing/bills/<id>
# Returns single bill with all items
# ─────────────────────────────────────────
@billing_bp.route('/api/billing/bills/<int:bill_id>', methods=['GET'])
def get_bill(bill_id):
    try:
        bill = Bill.query.get_or_404(bill_id)
        return jsonify({ 'success': True, 'data': bill.to_dict() })
    except Exception as e:
        return jsonify({ 'success': False, 'error': str(e) }), 500


# ─────────────────────────────────────────
# POST /api/billing/checkout
# Creates a new bill from cart items
# Body: { items: [{product_id, quantity, unit_price}], notes }
# ─────────────────────────────────────────
@billing_bp.route('/api/billing/checkout', methods=['POST'])
def checkout():
    try:
        data  = request.get_json()
        items = data.get('items', [])
        notes = data.get('notes', '')

        # Validation
        if not items:
            return jsonify({
                'success': False,
                'error'  : 'Cart is empty!'
            }), 400

        if len(items) < 1:
            return jsonify({
                'success': False,
                'error'  : 'Add at least one item!'
            }), 400

        # Validate all products exist
        # and have enough stock
        warnings = []
        for item in items:
            product = Product.query.get(item['product_id'])
            if not product:
                return jsonify({
                    'success': False,
                    'error'  : f"Product ID {item['product_id']} not found!"
                }), 404

            if product.current_stock < item['quantity']:
                return jsonify({
                    'success': False,
                    'error'  : f"Not enough stock for {product.name}! "
                               f"Available: {product.current_stock}, "
                               f"Requested: {item['quantity']}"
                }), 400

        # Create Bill
        bill_number = generate_bill_number()
        new_bill    = Bill(
            bill_number = bill_number,
            date        = date.today(),
            notes       = notes,
        )
        db.session.add(new_bill)
        db.session.flush()  # Get bill ID without committing

        total_amount = 0
        total_cost   = 0

        # Add each item
        for item in items:
            product    = Product.query.get(item['product_id'])
            qty        = int(item['quantity'])
            unit_price = float(item['unit_price'])
            unit_cost  = float(product.purchase_price)
            total_price = round(unit_price * qty, 2)

            bill_item = BillItem(
                bill_id    = new_bill.id,
                product_id = product.id,
                quantity   = qty,
                unit_price = unit_price,
                total_price= total_price,
                unit_cost  = unit_cost,
            )
            db.session.add(bill_item)

            # Deduct stock
            product.current_stock -= qty

            # Check low stock warning
            if product.current_stock <= product.reorder_level:
                warnings.append(
                    f"⚠️ Low stock: {product.name} "
                    f"({product.current_stock} left)"
                )

            total_amount += total_price
            total_cost   += unit_cost * qty

        # Update bill totals
        new_bill.total_amount = round(total_amount, 2)
        new_bill.total_cost   = round(total_cost, 2)
        new_bill.total_profit = round(total_amount - total_cost, 2)

        db.session.commit()

        response = {
            'success'    : True,
            'message'    : f'Bill {bill_number} created successfully!',
            'bill_number': bill_number,
            'bill_id'    : new_bill.id,
            'total'      : new_bill.total_amount,
            'profit'     : new_bill.total_profit,
        }

        if warnings:
            response['warnings'] = warnings

        return jsonify(response), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({ 'success': False, 'error': str(e) }), 500


# ─────────────────────────────────────────
# DELETE /api/billing/bills/<id>
# Deletes a bill (restores stock)
# ─────────────────────────────────────────
@billing_bp.route('/api/billing/bills/<int:bill_id>', methods=['DELETE'])
def delete_bill(bill_id):
    try:
        bill = Bill.query.get_or_404(bill_id)

        # Restore stock for each item
        for item in bill.items:
            product = Product.query.get(item.product_id)
            if product:
                product.current_stock += item.quantity

        db.session.delete(bill)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Bill {bill.bill_number} deleted and stock restored!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({ 'success': False, 'error': str(e) }), 500