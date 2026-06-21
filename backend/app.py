# app.py
# This is the MAIN file of our entire backend
# Think of it as the "front door" of our shop system
# Running this file starts the entire server

from flask import Flask, send_from_directory
from flask_cors import CORS
from database import init_db, db
import os
from routes.products import products_bp
from routes.sales import sales_bp
from routes.charts import charts_bp
from routes.predictions import predictions_bp
from routes.chatbot import chatbot_bp
from routes.billing import billing_bp
from routes.auth import auth_bp

def create_app():
    """
    This function builds and configures our Flask app.
    It connects the database, routes, and settings together.
    """

    # Step 1: Create the Flask application
    app = Flask(__name__)
    app.secret_key = 'shopmanager-secret-key-2026-change-this'
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['SESSION_COOKIE_SECURE']   = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    from datetime import timedelta
    app.permanent_session_lifetime = timedelta(hours=12)

    # Step 2: Enable CORS
    # CORS allows our frontend (HTML) to talk to our backend (Flask)
    # Without this, the browser blocks the connection for security
    CORS(app,
         origins="*",
         allow_headers=["Content-Type",
                        "X-Auth-Token",
                        "Accept"],
         methods=["GET", "POST", "PUT",
                  "DELETE", "OPTIONS"])

    # Step 3: Connect the database
    init_db(app)

    # Step 4: Register blueprints (route files)
    # This tells Flask: "these files contain URL routes, include them"
    app.register_blueprint(products_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(charts_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(auth_bp)

    # ── Health check endpoint ──
    @app.route('/api/health')
    def health():
        return {
            'success': True,
            'status' : 'Server is running!',
            'version': '2.0'
        }

    # ── Serve frontend home page ──
    @app.route('/')
    def home():
        return send_from_directory(
            os.path.join(
                os.path.dirname(
                    os.path.dirname(__file__)
                ), 'frontend'),
            'login.html'
        )

    # ── Serve all other frontend pages ──
    @app.route('/<path:filename>')
    def serve_frontend(filename):
        frontend_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(__file__)
            ), 'frontend')
        return send_from_directory(frontend_dir, filename)

    # ── 404 Handler ──
    @app.errorhandler(404)
    def not_found(e):
        return {
            'success': False,
            'error'  : 'The requested resource was not found.',
            'code'   : 404
        }, 404

    # ── 405 Handler ──
    @app.errorhandler(405)
    def method_not_allowed(e):
        return {
            'success': False,
            'error'  : 'Method not allowed.',
            'code'   : 405
        }, 405

    # ── 500 Handler ──
    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return {
            'success': False,
            'error'  : 'Internal server error. Please try again.',
            'code'   : 500
        }, 500

    # ── 400 Handler ──
    @app.errorhandler(400)
    def bad_request(e):
        return {
            'success': False,
            'error'  : 'Bad request. Please check your input.',
            'code'   : 400
        }, 400

    return app


# This block runs only when you execute: python app.py
# It will NOT run if this file is imported by another file
if __name__ == '__main__':
    app = create_app()
    app.run(
    debug = True,
    port  = 5000,
    host  = '0.0.0.0'
)