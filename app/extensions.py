"""Shared Flask extensions, instantiated once and imported everywhere."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
