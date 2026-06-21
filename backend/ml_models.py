# ml_models.py
# This is the BRAIN of our prediction system
# It contains 3 ML models:
# 1. Profit Predictor
# 2. Demand Forecaster
# 3. Stock Recommender

import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from sklearn.linear_model import LinearRegression


# ─────────────────────────────────────────
# MODEL 1: Profit Predictor
# Predicts next 7 days profit
# Based on: historical daily profit pattern
# ─────────────────────────────────────────
def predict_profit(sales_data, expenses_data):
    """
    Takes historical sales and expenses,
    predicts profit for next 7 days.

    Think of it like this:
    - Looks at past profit numbers
    - Finds the trend (going up or down?)
    - Projects that trend into the future
    """
    try:
        # Need at least 3 days of data to predict
        if len(sales_data) < 3:
            return {
                'success': False,
                'message': 'Need at least 3 days of sales data for prediction. Keep recording daily sales!',
                'predictions': []
            }

        # Build a dataframe from sales data
        df = pd.DataFrame(sales_data)
        df['date']    = pd.to_datetime(df['date'])
        df            = df.sort_values('date')

        # Calculate daily profit
        # Profit = Revenue - Cost of goods
        daily_profit = df.groupby('date').apply(
            lambda x: (
                x['revenue'].sum() -
                (x['purchase_price'] * x['quantity_sold']).sum()
            )
        ).reset_index()
        daily_profit.columns = ['date', 'profit']

        # Subtract daily expenses from profit
        if expenses_data:
            exp_df = pd.DataFrame(expenses_data)
            exp_df['date'] = pd.to_datetime(exp_df['date'])
            daily_exp = exp_df.groupby('date')['amount'].sum().reset_index()

            daily_profit = daily_profit.merge(
                daily_exp, on='date', how='left'
            )
            daily_profit['amount']  = daily_profit['amount'].fillna(0)
            daily_profit['profit'] -= daily_profit['amount']

        # Create numeric day index for ML model
        # (ML works with numbers, not dates)
        daily_profit['day_index'] = range(len(daily_profit))

        X = daily_profit[['day_index']].values
        y = daily_profit['profit'].values

        # Train Linear Regression model
        # This finds the best line through our data points
        model = LinearRegression()
        model.fit(X, y)

        # Predict next 7 days
        last_index   = daily_profit['day_index'].max()
        last_date    = daily_profit['date'].max()
        predictions  = []

        for i in range(1, 8):
            future_index  = last_index + i
            future_date   = last_date + timedelta(days=i)
            predicted_val = model.predict([[future_index]])[0]

            # Profit cannot be lower than -total expenses
            predicted_val = max(predicted_val, -50000)

            predictions.append({
                'date'  : future_date.strftime('%Y-%m-%d'),
                'day'   : future_date.strftime('%A'),
                'profit': round(float(predicted_val), 2)
            })

        # Calculate trend direction
        trend = 'increasing' if model.coef_[0] > 0 else 'decreasing'

        return {
            'success'    : True,
            'predictions': predictions,
            'trend'      : trend,
            'message'    : f'Profit trend is {trend} by Rs. {abs(round(model.coef_[0], 2))} per day'
        }

    except Exception as e:
        return {
            'success': False,
            'message': f'Prediction error: {str(e)}',
            'predictions': []
        }


# ─────────────────────────────────────────
# MODEL 2: Demand Forecaster
# Predicts how much of each product will sell
# Based on: past sales quantity per product
# ─────────────────────────────────────────
def forecast_demand(sales_data):
    """
    Looks at sales history per product
    and predicts next 7 days demand.

    Like a supermarket knowing:
    "We sell 50 bottles of water every hot day"
    """
    try:
        if len(sales_data) < 3:
            return {
                'success': False,
                'message': 'Need more sales data for demand forecasting.',
                'forecasts': []
            }

        df = pd.DataFrame(sales_data)
        df['date'] = pd.to_datetime(df['date'])

        forecasts = []

        # Forecast for each product separately
        for product_id in df['product_id'].unique():
            product_df   = df[df['product_id'] == product_id].copy()
            product_name = product_df['product_name'].iloc[0]

            # Group by date — total units sold per day
            daily_sales = product_df.groupby('date')[
                'quantity_sold'
            ].sum().reset_index()
            daily_sales = daily_sales.sort_values('date')
            daily_sales['day_index'] = range(len(daily_sales))

            # Need at least 2 data points
            if len(daily_sales) < 2:
                avg_sales = daily_sales['quantity_sold'].mean()
                forecasts.append({
                    'product_id'     : int(product_id),
                    'product_name'   : product_name,
                    'next_7_days'    : round(avg_sales * 7, 0),
                    'daily_average'  : round(avg_sales, 1),
                    'trend'          : 'stable',
                    'recommendation' : f'Keep at least {int(avg_sales * 10)} units in stock'
                })
                continue

            X = daily_sales[['day_index']].values
            y = daily_sales['quantity_sold'].values

            model = LinearRegression()
            model.fit(X, y)

            # Predict next 7 days total demand
            last_index   = daily_sales['day_index'].max()
            total_demand = 0

            for i in range(1, 8):
                pred = model.predict([[last_index + i]])[0]
                total_demand += max(0, pred)

            avg_daily = daily_sales['quantity_sold'].mean()
            trend     = 'increasing' if model.coef_[0] > 0.1 \
                        else 'decreasing' if model.coef_[0] < -0.1 \
                        else 'stable'

            # Smart recommendation based on trend
            if trend == 'increasing':
                rec = f'Demand rising! Stock at least {int(total_demand * 1.2)} units'
            elif trend == 'decreasing':
                rec = f'Demand slowing. Stock {int(total_demand * 0.8)} units is enough'
            else:
                rec = f'Stable demand. Keep {int(total_demand)} units ready'

            forecasts.append({
                'product_id'    : int(product_id),
                'product_name'  : product_name,
                'next_7_days'   : round(total_demand, 0),
                'daily_average' : round(float(avg_daily), 1),
                'trend'         : trend,
                'recommendation': rec
            })

        return {
            'success'  : True,
            'forecasts': forecasts,
            'message'  : f'Demand forecast ready for {len(forecasts)} products'
        }

    except Exception as e:
        return {
            'success'  : False,
            'message'  : f'Forecast error: {str(e)}',
            'forecasts': []
        }


# ─────────────────────────────────────────
# MODEL 3: Stock Recommender
# Tells you WHAT to restock and HOW MUCH
# Based on: current stock + daily sales rate
# ─────────────────────────────────────────
def recommend_stock(products_data, sales_data):
    """
    You were right — this one is the most logical!
    It calculates:
    - How fast each product is selling
    - How many days until stock runs out
    - How much to order
    """
    try:
        if not products_data:
            return {
                'success'        : False,
                'message'        : 'No products found.',
                'recommendations': []
            }

        recommendations = []

        # Calculate average daily sales per product
        daily_sales_map = {}
        if sales_data:
            df = pd.DataFrame(sales_data)
            df['date'] = pd.to_datetime(df['date'])

            # Only look at last 7 days for realistic average
            seven_days_ago = datetime.now() - timedelta(days=7)
            recent_df      = df[df['date'] >= seven_days_ago]

            if len(recent_df) > 0:
                avg_sales = recent_df.groupby('product_id')[
                    'quantity_sold'
                ].mean()
                daily_sales_map = avg_sales.to_dict()

        for product in products_data:
            pid           = product['id']
            current_stock = product['current_stock']
            reorder_level = product['reorder_level']
            avg_daily     = daily_sales_map.get(pid, 0)

            # Calculate days until stock runs out
            if avg_daily > 0:
                days_remaining = current_stock / avg_daily
            else:
                days_remaining = 999  # Not selling = no urgency

            # Determine urgency level
            if current_stock <= 0:
                urgency = 'critical'
                action  = '🔴 OUT OF STOCK — Order immediately!'
            elif current_stock <= reorder_level:
                urgency = 'high'
                action  = f'🟠 Below reorder level — Order today!'
            elif days_remaining <= 3:
                urgency = 'high'
                action  = f'🟠 Only {int(days_remaining)} days left — Order soon!'
            elif days_remaining <= 7:
                urgency = 'medium'
                action  = f'🟡 About {int(days_remaining)} days left — Plan reorder'
            else:
                urgency = 'low'
                action  = f'🟢 Good stock — {int(days_remaining)} days remaining'

            # Recommended order quantity
            # Order enough for 14 days based on current sales rate
            recommended_order = max(0, int(avg_daily * 14) - current_stock)
            if recommended_order == 0 and urgency in ['critical', 'high']:
                recommended_order = reorder_level * 2

            recommendations.append({
                'product_id'       : pid,
                'product_name'     : product['name'],
                'current_stock'    : current_stock,
                'reorder_level'    : reorder_level,
                'avg_daily_sales'  : round(float(avg_daily), 1),
                'days_remaining'   : round(float(days_remaining), 1)
                                     if days_remaining != 999 else 'N/A',
                'urgency'          : urgency,
                'action'           : action,
                'recommended_order': recommended_order
            })

        # Sort by urgency (critical first)
        urgency_order = {'critical': 0, 'high': 1,
                         'medium': 2, 'low': 3}
        recommendations.sort(
            key=lambda x: urgency_order.get(x['urgency'], 4)
        )

        return {
            'success'        : True,
            'recommendations': recommendations,
            'message'        : f'Stock analysis complete for {len(recommendations)} products'
        }

    except Exception as e:
        return {
            'success'        : False,
            'message'        : f'Stock analysis error: {str(e)}',
            'recommendations': []
        }