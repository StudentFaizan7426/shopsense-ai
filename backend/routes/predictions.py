# routes/predictions.py
# This file connects ML models to API endpoints
# Frontend calls these URLs to get predictions

from flask import Blueprint, jsonify
from database import db
from models import DailySale, Product, Expense
from ml_models import predict_profit, forecast_demand, recommend_stock

predictions_bp = Blueprint('predictions', __name__)


# ─────────────────────────────────────────
# API 1: Profit Prediction
# URL: GET /api/predictions/profit
# ─────────────────────────────────────────
@predictions_bp.route('/api/predictions/profit', methods=['GET'])
def get_profit_prediction():
    """
    Collects all sales & expenses from database
    then passes to ML model for prediction
    """
    try:
        # Get all sales with product info
        sales = DailySale.query.all()
        sales_data = []
        for s in sales:
            sales_data.append({
                'date'          : str(s.date),
                'product_id'    : s.product_id,
                'product_name'  : s.product.name,
                'quantity_sold' : s.quantity_sold,
                'revenue'       : s.revenue or 0,
                'purchase_price': s.product.purchase_price
            })

        # Get all expenses
        expenses      = Expense.query.all()
        expenses_data = [{
            'date'  : str(e.date),
            'amount': e.amount
        } for e in expenses]

        # Call ML model
        result = predict_profit(sales_data, expenses_data)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ─────────────────────────────────────────
# API 2: Demand Forecast
# URL: GET /api/predictions/demand
# ─────────────────────────────────────────
@predictions_bp.route('/api/predictions/demand', methods=['GET'])
def get_demand_forecast():
    """
    Collects sales history per product
    and predicts future demand
    """
    try:
        sales      = DailySale.query.all()
        sales_data = []
        for s in sales:
            sales_data.append({
                'date'         : str(s.date),
                'product_id'   : s.product_id,
                'product_name' : s.product.name,
                'quantity_sold': s.quantity_sold,
                'revenue'      : s.revenue or 0
            })

        result = forecast_demand(sales_data)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ─────────────────────────────────────────
# API 3: Stock Recommendations
# URL: GET /api/predictions/stock
# ─────────────────────────────────────────
@predictions_bp.route('/api/predictions/stock', methods=['GET'])
def get_stock_recommendations():
    """
    Analyzes current stock levels vs sales rate
    and gives reorder recommendations
    """
    try:
        # Get all products
        products      = Product.query.all()
        products_data = [p.to_dict() for p in products]

        # Get recent sales
        sales      = DailySale.query.all()
        sales_data = []
        for s in sales:
            sales_data.append({
                'date'         : str(s.date),
                'product_id'   : s.product_id,
                'product_name' : s.product.name,
                'quantity_sold': s.quantity_sold
            })

        result = recommend_stock(products_data, sales_data)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ─────────────────────────────────────────
# API 4: All predictions in one call
# URL: GET /api/predictions/all
# ─────────────────────────────────────────
@predictions_bp.route('/api/predictions/all', methods=['GET'])
def get_all_predictions():
    """
    Returns all 3 predictions in one API call
    Used by dashboard to load everything at once
    """
    try:
        # Collect data once, use for all models
        sales      = DailySale.query.all()
        sales_data = []
        for s in sales:
            sales_data.append({
                'date'          : str(s.date),
                'product_id'    : s.product_id,
                'product_name'  : s.product.name,
                'quantity_sold' : s.quantity_sold,
                'revenue'       : s.revenue or 0,
                'purchase_price': s.product.purchase_price
            })

        expenses      = Expense.query.all()
        expenses_data = [{
            'date'  : str(e.date),
            'amount': e.amount
        } for e in expenses]

        products      = Product.query.all()
        products_data = [p.to_dict() for p in products]

        # Run all 3 models
        profit_result = predict_profit(sales_data, expenses_data)
        demand_result = forecast_demand(sales_data)
        stock_result  = recommend_stock(products_data, sales_data)

        return jsonify({
            'success'        : True,
            'profit_prediction': profit_result,
            'demand_forecast'  : demand_result,
            'stock_recommendations': stock_result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500