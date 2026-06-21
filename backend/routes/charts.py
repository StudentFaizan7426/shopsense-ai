# routes/charts.py
# This file provides data specifically for our charts
# Think of it as a "data supplier" for the visual graphs

from flask import Blueprint, jsonify
from database import db
from models import DailySale, Expense, Product
from datetime import datetime, date, timedelta
from sqlalchemy import func

charts_bp = Blueprint('charts', __name__)


# ─────────────────────────────────────────
# API 1: Last 7 days profit trend
# Used for: Line Chart on dashboard
# URL: GET /api/charts/profit-trend
# ─────────────────────────────────────────
@charts_bp.route('/api/charts/profit-trend', methods=['GET'])
def profit_trend():
    """
    Returns profit data for the last 7 days.
    Each day shows: revenue, cost, and profit.
    """
    today  = date.today()
    labels = []
    revenue_data = []
    profit_data  = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)

        # Get all sales for this day
        sales = DailySale.query.filter(
            DailySale.date == day
        ).all()

        # Calculate revenue and cost for this day
        day_revenue = sum(s.revenue or 0 for s in sales)
        day_cost    = sum(
            s.product.purchase_price * s.quantity_sold
            for s in sales
        )
        day_profit  = day_revenue - day_cost

        # Format day label nicely e.g. "Mon 25"
        labels.append(day.strftime('%a %d'))
        revenue_data.append(round(day_revenue, 2))
        profit_data.append(round(day_profit, 2))

    return jsonify({
        'success': True,
        'data': {
            'labels'  : labels,
            'revenue' : revenue_data,
            'profit'  : profit_data
        }
    })


# ─────────────────────────────────────────
# API 2: Top selling products
# Used for: Bar Chart on dashboard
# URL: GET /api/charts/top-products
# ─────────────────────────────────────────

@charts_bp.route('/api/charts/top-products', methods=['GET'])
def top_products():
    """
    Returns top 5 best selling products
    of the CURRENT MONTH only (not all time).
    """
    from datetime import date

    # Get first day of current month
    today       = date.today()
    month_start = today.replace(day=1)

    # Query sales of this month only
    results = db.session.query(
        Product.name,
        db.func.sum(DailySale.quantity_sold).label('total_sold')
    ).join(
        DailySale, DailySale.product_id == Product.id
    ).filter(
        DailySale.date >= month_start
    ).group_by(
        Product.id
    ).order_by(
        db.func.sum(DailySale.quantity_sold).desc()
    ).limit(5).all()

    if not results:
        return jsonify({
            'success': True,
            'data'   : { 'labels': [], 'sold': [] },
            'message': 'No sales recorded this month yet.'
        })

    return jsonify({
        'success': True,
        'data': {
            'labels': [r.name for r in results],
            'sold'  : [r.total_sold for r in results],
            'period': f"{month_start} to {today}"
        }
    })

# ─────────────────────────────────────────
# API 3: Expense breakdown by category
# Used for: Pie Chart on dashboard
# URL: GET /api/charts/expenses-breakdown
# ─────────────────────────────────────────
@charts_bp.route('/api/charts/expenses-breakdown', methods=['GET'])
def expenses_breakdown():
    """
    Returns total expenses grouped by category.
    """
    results = db.session.query(
        Expense.category,
        func.sum(Expense.amount).label('total')
    ).group_by(Expense.category)\
     .order_by(func.sum(Expense.amount).desc())\
     .all()

    if not results:
        return jsonify({
            'success': True,
            'data': {
                'labels': [],
                'amounts': []
            }
        })

    return jsonify({
        'success': True,
        'data': {
            'labels' : [r.category for r in results],
            'amounts': [round(float(r.total), 2)
                        for r in results]
        }
    })