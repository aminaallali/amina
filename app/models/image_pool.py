from app import db


class ImageAsset(db.Model):
    __tablename__ = "image_assets"

    id = db.Column(db.Integer, primary_key=True)
    public_hash = db.Column(db.String(32), unique=True, nullable=False, index=True)
    category = db.Column(db.String(1), nullable=False, index=True)
    category_index = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    encrypted_data = db.Column(db.LargeBinary, nullable=True)

    __table_args__ = (db.UniqueConstraint("category", "category_index"),)
