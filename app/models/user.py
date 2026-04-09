from app.db.database import db
from sqlalchemy.sql import func

class User(db.Model):
    __tablename__ = 'users'

    id  = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    hash_password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    modify_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

