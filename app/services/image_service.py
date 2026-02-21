import base64
import hashlib
import io
import os
import random
import secrets
from typing import Dict, List

from PIL import Image

from app import db
from app.models.image_pool import ImageAsset


class ImageService:
    def __init__(self, config):
        self.config = config
        self.tile_size = config.IMAGE_TILE_SIZE

    def initialize_image_pool(self, source_directory: str, category: str) -> int:
        imported = 0
        os.makedirs(os.path.join("images", f"pool_{category.lower()}"), exist_ok=True)

        for idx, filename in enumerate(sorted(os.listdir(source_directory))):
            if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                continue

            source_path = os.path.join(source_directory, filename)
            public_hash = secrets.token_hex(16)
            processed_data = self._process_image(source_path)

            new_filename = f"{public_hash}.{self.config.IMAGE_SERVE_FORMAT}"
            dest_path = os.path.join("images", f"pool_{category.lower()}", new_filename)
            with open(dest_path, "wb") as f:
                f.write(processed_data)

            db.session.add(
                ImageAsset(
                    public_hash=public_hash,
                    category=category,
                    category_index=idx,
                    file_path=dest_path,
                    encrypted_data=processed_data,
                )
            )
            imported += 1

        db.session.commit()
        return imported

    def _process_image(self, source_path: str) -> bytes:
        img = Image.open(source_path)
        data = list(img.getdata())
        clean_img = Image.new(img.mode, img.size)
        clean_img.putdata(data)
        clean_img = clean_img.resize(self.tile_size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        clean_img.save(buffer, format="WEBP", quality=85)
        return buffer.getvalue()

    def assign_images_to_user(self, wheel_size: int) -> Dict[str, List[int]]:
        cat_a_images = ImageAsset.query.filter_by(category="A", is_active=True).all()
        cat_b_images = ImageAsset.query.filter_by(category="B", is_active=True).all()

        if len(cat_a_images) < wheel_size or len(cat_b_images) < wheel_size:
            raise ValueError("عدد الصور في المخزن غير كافٍ")

        secure_random = random.SystemRandom()
        outer_selection = secure_random.sample([img.id for img in cat_a_images], wheel_size)
        inner_selection = secure_random.sample([img.id for img in cat_b_images], wheel_size)
        return {"outer": outer_selection, "inner": inner_selection}

    def generate_canvas_data(self, outer_wheel_order: List[int], inner_wheel_order: List[int], session_seed: str) -> dict:
        tile_w, tile_h = self.tile_size
        all_ids = outer_wheel_order + inner_wheel_order
        total_tiles = len(all_ids)

        cols = 10
        rows = max(1, (total_tiles + cols - 1) // cols)
        composite = Image.new("RGBA", (cols * tile_w, rows * tile_h))

        scatter_order = list(range(total_tiles))
        rng = random.Random(hashlib.sha256(session_seed.encode()).hexdigest())
        rng.shuffle(scatter_order)

        tile_positions = {}
        for visual_idx, actual_idx in enumerate(scatter_order):
            image_id = all_ids[actual_idx]
            asset = ImageAsset.query.get(image_id)
            if not asset or not asset.encrypted_data:
                continue

            tile_img = Image.open(io.BytesIO(asset.encrypted_data))
            row, col = divmod(visual_idx, cols)
            x, y = col * tile_w, row * tile_h
            composite.paste(tile_img, (x, y))
            tile_positions[str(actual_idx)] = self._encrypt_position(actual_idx, x, y, session_seed)

        buffer = io.BytesIO()
        composite.save(buffer, format="WEBP", quality=90)

        return {
            "composite_image": base64.b64encode(buffer.getvalue()).decode(),
            "tile_map": tile_positions,
            "canvas_dimensions": {"width": composite.width, "height": composite.height},
            "tile_size": {"width": tile_w, "height": tile_h},
            "outer_count": len(outer_wheel_order),
            "inner_count": len(inner_wheel_order),
        }

    def _encrypt_position(self, idx: int, x: int, y: int, seed: str) -> str:
        payload = f"{idx}:{x}:{y}"
        return hashlib.sha256(f"{seed}:{payload}".encode()).hexdigest()[:16]
