from app.services.shuffle_engine import ShuffleEngine


def test_derive_permutation_is_deterministic():
    engine = ShuffleEngine(5)
    p1 = engine.derive_permutation("seed", 10, 5)
    p2 = engine.derive_permutation("seed", 10, 5)
    assert p1 == p2
    assert len(p1) == 5


def test_verify_response_success():
    engine = ShuffleEngine(5)
    resp = {"inner_rotation": 3, "alignment_check": 1}
    expected = engine._hash_response(resp, "session")
    result = engine.verify_response(resp, expected, "session")
    assert result["is_valid"] is True
