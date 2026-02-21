from pathlib import Path

from flask import Blueprint, abort, send_file

from app.models.image_pool import ImageAsset

image_api = Blueprint("image_api", __name__, url_prefix="/api/v1")


@image_api.route("/images/<string:public_hash>", methods=["GET"])
def fetch_image(public_hash: str):
    asset = ImageAsset.query.filter_by(public_hash=public_hash, is_active=True).first()
    if not asset or not asset.file_path:
        abort(404)

    file_path = Path(asset.file_path)
    if not file_path.exists():
        abort(404)

    return send_file(file_path, mimetype="image/webp")
