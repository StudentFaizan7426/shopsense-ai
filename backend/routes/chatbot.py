# routes/chatbot.py
# AI Chatbot using Groq (Free & Fast!)

from flask import Blueprint, request, jsonify
from models import DailySale, Product, Expense
from datetime import date, timedelta
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

chatbot_bp = Blueprint('chatbot', __name__)
client = Groq(api_key=os.getenv('GROQ_API_KEY'))


def get_shop_context():
    today     = date.today()
    week_ago  = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    products      = Product.query.all()
    products_info = []
    for p in products:
        products_info.append(
            f"- {p.name} | Category: {p.category} | "
            f"Buy: Rs.{p.purchase_price} | "
            f"Sell: Rs.{p.selling_price} | "
            f"Profit/unit: Rs.{p.profit_per_unit()} | "
            f"Stock: {p.current_stock} units | "
            f"Reorder at: {p.reorder_level} units"
        )

    today_sales   = DailySale.query.filter(
        DailySale.date == today).all()
    today_revenue = sum(s.revenue or 0 for s in today_sales)
    today_cost    = sum(
        s.product.purchase_price * s.quantity_sold
        for s in today_sales)
    today_profit  = today_revenue - today_cost

    week_sales   = DailySale.query.filter(
        DailySale.date >= week_ago).all()
    week_revenue = sum(s.revenue or 0 for s in week_sales)
    week_cost    = sum(
        s.product.purchase_price * s.quantity_sold
        for s in week_sales)
    week_profit  = week_revenue - week_cost

    all_expenses   = Expense.query.all()
    today_expenses = sum(
        e.amount for e in all_expenses if e.date == today)
    month_expenses = sum(
        e.amount for e in all_expenses
        if e.date >= month_ago)

    exp_by_cat = {}
    for e in all_expenses:
        exp_by_cat[e.category] = \
            exp_by_cat.get(e.category, 0) + e.amount
    exp_breakdown = "\n".join([
        f"  - {cat}: Rs.{amt}"
        for cat, amt in exp_by_cat.items()
    ]) or "  - No expenses recorded"

    product_sales = {}
    for s in week_sales:
        name = s.product.name
        product_sales[name] = \
            product_sales.get(name, 0) + s.quantity_sold
    top_products = sorted(
        product_sales.items(),
        key=lambda x: x[1], reverse=True)[:3]
    top_str = "\n".join([
        f"  - {name}: {qty} units this week"
        for name, qty in top_products
    ]) or "  - No sales this week yet"

    low_stock = [
        p for p in products
        if p.current_stock <= p.reorder_level]
    low_stock_str = "\n".join([
        f"  - {p.name}: {p.current_stock} units left"
        for p in low_stock
    ]) or "  - All products have sufficient stock"

    return f"""
SHOP DATA REPORT — {today.strftime('%d %B %Y')}
{'='*50}

PRODUCTS ({len(products)} total):
{chr(10).join(products_info) or '- No products yet'}

TODAY'S PERFORMANCE:
  - Transactions: {len(today_sales)}
  - Revenue: Rs.{round(today_revenue, 2)}
  - Cost of goods: Rs.{round(today_cost, 2)}
  - Gross profit: Rs.{round(today_profit, 2)}
  - Expenses: Rs.{round(today_expenses, 2)}
  - Net profit: Rs.{round(today_profit - today_expenses, 2)}

LAST 7 DAYS:
  - Revenue: Rs.{round(week_revenue, 2)}
  - Cost: Rs.{round(week_cost, 2)}
  - Profit: Rs.{round(week_profit, 2)}

THIS MONTH EXPENSES: Rs.{round(month_expenses, 2)}
BREAKDOWN:
{exp_breakdown}

TOP PRODUCTS (Last 7 days):
{top_str}

LOW STOCK ALERTS:
{low_stock_str}
"""


@chatbot_bp.route('/api/chatbot', methods=['POST'])
def chat():
    data     = request.get_json()
    question = data.get('message', '').strip()

    if not question:
        return jsonify({
            'success': False,
            'error'  : 'Please ask a question!'
        }), 400

    try:
        shop_context = get_shop_context()

        completion = client.chat.completions.create(
            model    = "llama-3.3-70b-versatile",
            messages = [
                {
                    "role"   : "system",
                    "content": """You are a smart AI business 
assistant for a small shop owner in Pakistan.

Your job:
1. Analyze real shop data provided
2. Answer clearly and practically
3. Give specific advice based on REAL numbers
4. Keep responses to 3-5 sentences maximum
5. Use simple everyday English
6. Always use Pakistani Rupees (Rs.)
7. Be encouraging and supportive
8. Never make up numbers not in the data"""
                },
                {
                    "role"   : "user",
                    "content": f"""Here is my shop data:

{shop_context}

My question: {question}

Give a helpful answer based on the data above:"""
                }
            ],
            max_tokens  = 300,
            temperature = 0.7
        )

        response = completion.choices[0].message.content

        return jsonify({
            'success' : True,
            'response': response,
            'question': question
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error'  : f'Chatbot error: {str(e)}'
        }), 500


@chatbot_bp.route('/api/chatbot/suggestions', methods=['GET'])
def get_suggestions():
    suggestions = [
        "How is my shop performing today?",
        "Which product should I restock?",
        "Why is my profit low?",
        "What are my biggest expenses?",
        "Which product makes the most profit?",
        "How can I increase my shop revenue?",
        "Am I making a profit this week?",
        "What should I focus on to grow my business?"
    ]
    return jsonify({
        'success'    : True,
        'suggestions': suggestions
    })