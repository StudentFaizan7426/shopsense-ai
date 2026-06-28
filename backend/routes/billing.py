# routes/billing.py
# FIXED VERSION — Also saves to daily_sales table
# so Dashboard financial data updates correctly

from flask import Blueprint, request, jsonify
from database import db
from models import Product, Bill, BillItem, DailySale
from datetime import date, datetime

billing_bp = Blueprint('billing', __name__)

# ── Get all bills ──────────────────────────
@billing_bp.route('/api/billing/bills', methods=['GET'])
def get_bills():
    try:
        period = request.args.get('period', 'today')
        today  = date.today()

        if period == 'today':
            bills = Bill.query.filter(
                Bill.date == today
            ).order_by(Bill.created_at.desc()).all()
        else:
            bills = Bill.query.order_by(
                Bill.created_at.desc()
            ).all()

        # Calculate summary
        total_bills   = len(bills)
        total_revenue = sum(b.total_amount for b in bills)
        total_profit  = sum(b.total_profit  for b in bills)

        return jsonify({
            'success': True,
            'data'   : [b.to_dict() for b in bills],
            'summary': {
                'total_bills'  : total_bills,
                'total_revenue': round(total_revenue, 2),
                'total_profit' : round(total_profit,  2)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── Get single bill ────────────────────────
@billing_bp.route('/api/billing/bills/<int:bill_id>',
                  methods=['GET'])
def get_bill(bill_id):
    try:
        bill = Bill.query.get_or_404(bill_id)
        return jsonify({'success': True, 'data': bill.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── Checkout — Create Bill ─────────────────
@billing_bp.route('/api/billing/checkout', methods=['POST'])
def checkout():
    try:
        data  = request.get_json()
        items = data.get('items', [])
        notes = data.get('notes', '')

        if not items:
            return jsonify({
                'success': False,
                'error'  : 'Cart is empty!'
            }), 400

        # Generate bill number
        today      = date.today()
        bill_count = Bill.query.filter(
            Bill.date == today
        ).count()
        bill_number = (
            f"BILL-{today.strftime('%Y%m%d')}"
            f"-{str(bill_count + 1).zfill(3)}"
        )

        # Create bill
        bill = Bill(
            bill_number = bill_number,
            date        = today,
            notes       = notes
        )
        db.session.add(bill)
        db.session.flush()

        total_amount = 0
        total_cost   = 0
        warnings     = []

        for item_data in items:
            product = Product.query.get(item_data['product_id'])

            if not product:
                return jsonify({
                    'success': False,
                    'error'  : f'Product not found!'
                }), 404

            qty        = item_data['quantity']
            unit_price = item_data['unit_price']
            unit_cost  = product.purchase_price

            # Check stock
            if product.current_stock < qty:
                return jsonify({
                    'success': False,
                    'error'  : (
                        f'Not enough stock for '
                        f'{product.name}! '
                        f'Available: {product.current_stock}'
                    )
                }), 400

            # Create bill item
            bill_item = BillItem(
                bill_id     = bill.id,
                product_id  = product.id,
                quantity    = qty,
                unit_price  = unit_price,
                unit_cost   = unit_cost,
                total_price = round(unit_price * qty, 2)
            )
            db.session.add(bill_item)

            # ── FIX: Also save to daily_sales ──
            # This is what makes dashboard update!
            sale = DailySale(
                product_id    = product.id,
                quantity_sold = qty,
                sale_price    = unit_price,
                revenue       = round(unit_price * qty, 2),
                date          = today,
                notes         = f'Billed: {bill_number}'
            )
            db.session.add(sale)

            # Deduct stock
            product.current_stock -= qty

            # Check low stock warning
            if product.current_stock <= product.reorder_level:
                warnings.append(
                    f'⚠️ Low stock: {product.name} '
                    f'({product.current_stock} left)'
                )

            total_amount += unit_price * qty
            total_cost   += unit_cost  * qty

        # Update bill totals
        bill.total_amount = round(total_amount, 2)
        bill.total_cost   = round(total_cost,   2)
        bill.total_profit = round(
            total_amount - total_cost, 2
        )

        db.session.commit()

        return jsonify({
            'success' : True,
            'message' : f'Bill {bill_number} created!',
            'bill_id' : bill.id,
            'total'   : round(total_amount, 2),
            'warnings': warnings
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ── Delete Bill ────────────────────────────
@billing_bp.route('/api/billing/bills/<int:bill_id>',
                  methods=['DELETE'])
def delete_bill(bill_id):
    try:
        bill = Bill.query.get_or_404(bill_id)
        db.session.delete(bill)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Bill deleted!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
