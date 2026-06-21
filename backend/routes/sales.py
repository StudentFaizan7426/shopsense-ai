# routes/sales.py
# This file handles everything related to SALES
# Think of it as the "daily sales register" of our shop
# Every time a product is sold, it gets recorded here

from flask import Blueprint, request, jsonify
from database import db
from models import DailySale, Expense, Product
from datetime import datetime, date

# Blueprint for all sales-related routes
sales_bp = Blueprint('sales', __name__)


# ─────────────────────────────────────────
# JOB 1: GET all sales
# URL: GET http://localhost:5000/api/sales
# ─────────────────────────────────────────
@sales_bp.route('/api/sales', methods=['GET'])
def get_sales():
    """Returns all sales records"""
    sales = DailySale.query.order_by(DailySale.date.desc()).all()
    return jsonify({
        'success': True,
        'data'   : [s.to_dict() for s in sales],
        'count'  : len(sales)
    })


# ─────────────────────────────────────────
# JOB 2: RECORD a new sale
# URL: POST http://localhost:5000/api/sales
# ─────────────────────────────────────────
@sales_bp.route('/api/sales', methods=['POST'])
def record_sale():
    """
    Records a new sale AND automatically reduces stock.
    Example: Sold 5 Rice → stock goes from 50 to 45
    """
    data = request.get_json()

    # Check product exists
    product = Product.query.get(data.get('product_id'))
    if not product:
        return jsonify({
            'success': False,
            'error'  : 'Product not found!'
        }), 404

    # Check if enough stock is available
    quantity = int(data.get('quantity_sold', 0))
    if product.current_stock < quantity:
        return jsonify({
            'success': False,
            'error'  : f'Not enough stock! Only {product.current_stock} units available.'
        }), 400

    # Use today's date if no date provided
    sale_date = date.today()
    if 'date' in data:
        sale_date = datetime.strptime(data['date'], '%Y-%m-%d').date()

    # Use product's selling price if no price provided
    sale_price = float(data.get('sale_price', product.selling_price))

    # Create the sale record
    sale         = DailySale(
        product_id    = product.id,
        quantity_sold = quantity,
        sale_price    = sale_price,
        date          = sale_date,
        notes         = data.get('notes', '')
    )
    # Calculate revenue automatically
    sale.revenue = sale.calculate_revenue()

    # ✅ Reduce stock automatically
    product.current_stock -= quantity

    # Save everything to database
    db.session.add(sale)
    db.session.commit()

    # Warn if stock is now low
    warning = None
    if product.current_stock <= product.reorder_level:
        warning = f"⚠️ Low stock alert: Only {product.current_stock} units left for '{product.name}'"

    return jsonify({
        'success': True,
        'message': 'Sale recorded successfully!',
        'data'   : sale.to_dict(),
        'warning': warning
    }), 201


# ─────────────────────────────────────────
# JOB 3: GET today's profit summary
# URL: GET http://localhost:5000/api/sales/summary
# ─────────────────────────────────────────
@sales_bp.route('/api/sales/summary', methods=['GET'])
def get_summary():
    """
    Calculates today's profit summary.
    Profit = Revenue - Cost of goods sold - Expenses
    """
    today = date.today()

    # Get all sales for today
    sales = DailySale.query.filter(DailySale.date == today).all()

    # Calculate totals
    total_revenue = sum(s.revenue or 0 for s in sales)
    total_cost    = sum(
        s.product.purchase_price * s.quantity_sold
        for s in sales
    )
    gross_profit = total_revenue - total_cost

    # Get today's expenses
    expenses      = Expense.query.filter(Expense.date == today).all()
    total_expenses = sum(e.amount for e in expenses)

    # Net profit = gross profit minus expenses
    net_profit = gross_profit - total_expenses

    return jsonify({
        'success': True,
        'data': {
            'date'          : str(today),
            'total_revenue' : round(total_revenue, 2),
            'total_cost'    : round(total_cost, 2),
            'gross_profit'  : round(gross_profit, 2),
            'total_expenses': round(total_expenses, 2),
            'net_profit'    : round(net_profit, 2),
            'total_sales'   : len(sales)
        }
    })


# ─────────────────────────────────────────
# JOB 4: ADD an expense
# URL: POST http://localhost:5000/api/expenses
# ─────────────────────────────────────────
@sales_bp.route('/api/expenses', methods=['POST'])
def add_expense():
    """Records a shop expense like rent, electricity etc."""
    data = request.get_json()

    if 'category' not in data or 'amount' not in data:
        return jsonify({
            'success': False,
            'error'  : 'category and amount are required!'
        }), 400

    expense = Expense(
        category    = data['category'],
        amount      = float(data['amount']),
        date        = datetime.strptime(data['date'], '%Y-%m-%d').date() if 'date' in data else date.today(),
        description = data.get('description', '')
    )

    db.session.add(expense)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Expense recorded successfully!',
        'data'   : expense.to_dict()
    }), 201


# ─────────────────────────────────────────
# JOB 5: GET all expenses
# URL: GET http://localhost:5000/api/expenses
# ─────────────────────────────────────────
@sales_bp.route('/api/expenses', methods=['GET'])
def get_expenses():
    """Returns all recorded expenses"""
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    return jsonify({
        'success': True,
        'data'   : [e.to_dict() for e in expenses],
        'count'  : len(expenses)
    })
#What This File Does
#record_sale()  → records sale + auto reduces stock
#get_summary()  → calculates today's profit instantly
#add_expense()  → records rent, electricity etc.
#get_expenses() → shows all expenses
# ─────────────────────────────────────────
# Weekly & Monthly Revenue Summary
# URL: GET /api/sales/period-summary
# ─────────────────────────────────────────
@sales_bp.route('/api/sales/period-summary', methods=['GET'])
def period_summary():
    """
    Returns weekly and monthly profit summaries.
    Used by dashboard to show performance over time.
    """
    from datetime import datetime, date, timedelta

    today      = date.today()
    week_ago   = today - timedelta(days=7)
    month_start = today.replace(day=1)

    # ── Weekly Data (Last 7 days) ──
    week_sales = DailySale.query.filter(
        DailySale.date >= week_ago
    ).all()

    week_revenue = sum(s.revenue or 0 for s in week_sales)
    week_cost    = sum(
        s.product.purchase_price * s.quantity_sold
        for s in week_sales
    )
    week_profit  = week_revenue - week_cost

    week_expenses = Expense.query.filter(
        Expense.date >= week_ago
    ).all()
    week_exp_total = sum(e.amount for e in week_expenses)
    week_net       = week_profit - week_exp_total

    # ── Monthly Data (This month) ──
    month_sales = DailySale.query.filter(
        DailySale.date >= month_start
    ).all()

    month_revenue = sum(s.revenue or 0 for s in month_sales)
    month_cost    = sum(
        s.product.purchase_price * s.quantity_sold
        for s in month_sales
    )
    month_profit  = month_revenue - month_cost

    month_expenses = Expense.query.filter(
        Expense.date >= month_start
    ).all()
    month_exp_total = sum(e.amount for e in month_expenses)
    month_net       = month_profit - month_exp_total

    # ── Best selling product this month ──
    product_sales = {}
    for s in month_sales:
        name = s.product.name
        product_sales[name] = \
            product_sales.get(name, 0) + s.quantity_sold

    best_product = max(
        product_sales, key=product_sales.get
    ) if product_sales else 'No sales yet'

    return jsonify({
        'success': True,
        'data': {
            'weekly': {
                'revenue'     : round(week_revenue, 2),
                'cost'        : round(week_cost, 2),
                'gross_profit': round(week_profit, 2),
                'expenses'    : round(week_exp_total, 2),
                'net_profit'  : round(week_net, 2),
                'transactions': len(week_sales),
                'period'      : f"{week_ago} to {today}"
            },
            'monthly': {
                'revenue'     : round(month_revenue, 2),
                'cost'        : round(month_cost, 2),
                'gross_profit': round(month_profit, 2),
                'expenses'    : round(month_exp_total, 2),
                'net_profit'  : round(month_net, 2),
                'transactions': len(month_sales),
                'best_product': best_product,
                'period'      : f"{month_start} to {today}"
            }
        }
    })
# ─────────────────────────────────────────
# Full Report Data for PDF Generation
# URL: GET /api/reports/generate
# Query params: ?period=monthly OR ?period=weekly
# ─────────────────────────────────────────
@sales_bp.route('/api/reports/generate', methods=['GET'])
def generate_report():
    """
    Returns complete data for PDF report generation.
    Includes summary, best sellers, and expenses.
    """
    from datetime import date, timedelta

    period      = request.args.get('period', 'monthly')
    today       = date.today()

    if period == 'weekly':
        start_date  = today - timedelta(days=7)
        period_label = f"Weekly Report ({start_date} to {today})"
    else:
        start_date  = today.replace(day=1)
        period_label = f"Monthly Report ({start_date} to {today})"

    # ── Sales Summary ──
    period_sales = DailySale.query.filter(
        DailySale.date >= start_date
    ).all()

    total_revenue = sum(s.revenue or 0 for s in period_sales)
    total_cost    = sum(
        s.product.purchase_price * s.quantity_sold
        for s in period_sales
    )
    gross_profit  = total_revenue - total_cost
    transactions  = len(period_sales)

    # ── Expenses ──
    period_expenses = Expense.query.filter(
        Expense.date >= start_date
    ).all()
    total_expenses = sum(e.amount for e in period_expenses)
    net_profit     = gross_profit - total_expenses

    # ── Expense breakdown by category ──
    expense_by_cat = {}
    for e in period_expenses:
        expense_by_cat[e.category] = \
            expense_by_cat.get(e.category, 0) + e.amount

    # ── Best selling products ──
    product_sales = {}
    product_revenue = {}
    for s in period_sales:
        name = s.product.name
        product_sales[name] = \
            product_sales.get(name, 0) + s.quantity_sold
        product_revenue[name] = \
            product_revenue.get(name, 0) + (s.revenue or 0)

    top_products = sorted(
        product_sales.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    # ── Daily breakdown ──
    daily = {}
    for s in period_sales:
        d = str(s.date)
        if d not in daily:
            daily[d] = { 'revenue': 0, 'cost': 0, 'transactions': 0 }
        daily[d]['revenue']      += s.revenue or 0
        daily[d]['cost']         += s.product.purchase_price * s.quantity_sold
        daily[d]['transactions'] += 1

    daily_rows = [
        {
            'date'        : d,
            'revenue'     : round(v['revenue'], 2),
            'cost'        : round(v['cost'], 2),
            'profit'      : round(v['revenue'] - v['cost'], 2),
            'transactions': v['transactions']
        }
        for d, v in sorted(daily.items())
    ]

    return jsonify({
        'success': True,
        'data': {
            'period_label' : period_label,
            'start_date'   : str(start_date),
            'end_date'     : str(today),
            'period'       : period,
            'summary': {
                'total_revenue' : round(total_revenue, 2),
                'total_cost'    : round(total_cost, 2),
                'gross_profit'  : round(gross_profit, 2),
                'total_expenses': round(total_expenses, 2),
                'net_profit'    : round(net_profit, 2),
                'transactions'  : transactions,
            },
            'top_products': [
                {
                    'name'   : name,
                    'units'  : units,
                    'revenue': round(product_revenue.get(name, 0), 2)
                }
                for name, units in top_products
            ],
            'expenses_breakdown': [
                { 'category': cat, 'amount': round(amt, 2) }
                for cat, amt in sorted(
                    expense_by_cat.items(),
                    key=lambda x: x[1], reverse=True
                )
            ],
            'daily_breakdown': daily_rows
        }
    })