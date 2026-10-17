"""Trade Store application factory."""
from flask import Flask
from .extensions import db
from .config import config_by_name


def create_app(config_name: str = "development") -> Flask:
    """Create and configure the Flask application.

    Args:
        config_name: One of 'development', 'testing', 'production'.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from .routes.trade_routes import trade_bp
    app.register_blueprint(trade_bp, url_prefix="/api/v1")

    # Create tables
    with app.app_context():
        db.create_all()

    return app
