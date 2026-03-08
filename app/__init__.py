"""Flask application factory."""
import os
from flask import Flask, jsonify, session, redirect, url_for, request
from app.extensions import db
from app.utils import inject_orgs


def create_app():
    """Create and configure the Flask application."""
    # Determine project root (parent of app/ package)
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    app = Flask(
        __name__,
        template_folder=os.path.join(basedir, 'templates'),
        static_folder=os.path.join(basedir, 'static')
    )

    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'fumehoods.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'super_secret_dev_key'

    upload_folder = os.path.join(basedir, 'static', 'uploads')
    app.config['UPLOAD_FOLDER'] = upload_folder
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(os.path.join(basedir, 'static', 'qrcodes'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register context processor
    app.context_processor(inject_orgs)

    # Register blueprints
    from app.routes.dashboard import dashboard_bp
    from app.routes.organizations import organizations_bp
    from app.routes.hoods import hoods_bp
    from app.routes.settings import settings_bp
    from app.routes.technicians import technicians_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(organizations_bp)
    app.register_blueprint(hoods_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(technicians_bp)
    app.register_blueprint(auth_bp)

    # Authentication guard — redirect to login if not logged in
    @app.before_request
    def require_login():
        allowed = ('auth.login', 'auth.logout', 'static')
        if request.endpoint and request.endpoint not in allowed:
            # Allow print/certificate pages that open in new tabs
            if not session.get('logged_in'):
                return redirect(url_for('auth.login'))

    # Seed API route (kept at app level since it touches all models)
    from app.seed import seed_data

    @app.route('/api/seed', methods=['POST'])
    def api_seed():
        result, status = seed_data()
        return jsonify(result), status

    return app
