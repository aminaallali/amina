import hashlib
import hmac
import json
import secrets
from datetime import datetime
from typing import List, Optional


class ShuffleEngine:
    def __init__(self, wheel_size: int = 20):
        self.wheel_size = wheel_size

    def generate_seed(self, entropy_bits: int = 256) -> str:
        return secrets.token_hex(entropy_bits // 8)

    def derive_permutation(self, seed: str, pool_size: int, wheel_size: int = None) -> List[int]:
        if wheel_size is None:
            wheel_size = self.wheel_size
        if pool_size <= 0:
            return []

        indices = list(range(pool_size))
        result = []
        for i in range(min(wheel_size, pool_size)):
            hmac_input = f"{seed}:{i}".encode("utf-8")
            hash_val = hmac.new(seed.encode("utf-8"), hmac_input, hashlib.sha256).hexdigest()
            idx = int(hash_val[:8], 16) % len(indices)
            result.append(indices.pop(idx))
        return result

    def circular_shift(self, wheel: List[int], steps: int) -> List[int]:
        n = len(wheel)
        if n == 0:
            return wheel
        steps = steps % n
        return wheel[-steps:] + wheel[:-steps]

    def find_image_position(self, wheel: List[int], image_id: int) -> Optional[int]:
        try:
            return wheel.index(image_id)
        except ValueError:
            return None

    def generate_challenge(self, base_seed: str, assigned_images: dict, secret_offset_outer: int, secret_offset_inner: int) -> dict:
        session_seed = self.generate_seed()

        outer_perm = self.derive_permutation(f"{session_seed}:outer", len(assigned_images["outer"]), self.wheel_size)
        inner_perm = self.derive_permutation(f"{session_seed}:inner", len(assigned_images["inner"]), self.wheel_size)

        outer_wheel_shuffled = [assigned_images["outer"][i] for i in outer_perm]
        inner_wheel_shuffled = [assigned_images["inner"][i] for i in inner_perm]

        expected = self._calculate_expected_response(
            outer_wheel_shuffled,
            inner_wheel_shuffled,
            assigned_images,
            secret_offset_outer,
            secret_offset_inner,
            base_seed,
        )
        expected_hash = self._hash_response(expected, session_seed)

        return {
            "session_seed": session_seed,
            "outer_wheel_order": outer_wheel_shuffled,
            "inner_wheel_order": inner_wheel_shuffled,
            "expected_response_hash": expected_hash,
            "expected_response_raw": expected,
        }

    def _calculate_expected_response(self, outer_shuffled, inner_shuffled, assigned_images, secret_offset_outer, secret_offset_inner, base_seed):
        secret_images = self._derive_secret_images(base_seed, assigned_images)
        outer_pos = self.find_image_position(outer_shuffled, secret_images["outer"])
        inner_pos = self.find_image_position(inner_shuffled, secret_images["inner"])

        if outer_pos is None or inner_pos is None:
            return {"inner_rotation": 0, "alignment_check": 0}

        required_inner_rotation = (outer_pos - inner_pos) % max(1, len(inner_shuffled))
        return {"inner_rotation": required_inner_rotation, "alignment_check": (outer_pos + inner_pos) % self.wheel_size}

    def _derive_secret_images(self, base_seed: str, assigned_images: dict) -> dict:
        outer_hash = hmac.new(base_seed.encode(), b"outer_secret", hashlib.sha256).hexdigest()
        inner_hash = hmac.new(base_seed.encode(), b"inner_secret", hashlib.sha256).hexdigest()

        outer_idx = int(outer_hash[:8], 16) % len(assigned_images["outer"])
        inner_idx = int(inner_hash[:8], 16) % len(assigned_images["inner"])

        return {"outer": assigned_images["outer"][outer_idx], "inner": assigned_images["inner"][inner_idx]}

    def verify_response(self, user_response: dict, expected_hash: str, session_seed: str, tolerance: int = 0) -> dict:
        user_hash = self._hash_response(
            {
                "inner_rotation": user_response["inner_rotation"],
                "alignment_check": user_response.get("alignment_check", 0),
            },
            session_seed,
        )
        is_match = hmac.compare_digest(user_hash, expected_hash)

        if not is_match and tolerance > 0:
            for t in range(-tolerance, tolerance + 1):
                adjusted = {
                    "inner_rotation": (user_response["inner_rotation"] + t) % self.wheel_size,
                    "alignment_check": user_response.get("alignment_check", 0),
                }
                if hmac.compare_digest(self._hash_response(adjusted, session_seed), expected_hash):
                    is_match = True
                    break

        return {"is_valid": is_match, "timestamp": datetime.utcnow().isoformat()}

    def _hash_response(self, response: dict, session_seed: str) -> str:
        payload = json.dumps(response, sort_keys=True)
        return hmac.new(session_seed.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
