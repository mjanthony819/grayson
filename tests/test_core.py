import math

from grayson.core import (ACTION_BY_ID, actions_for, kind_of, slice_index,
                          slice_mid_angle, unique_output)


def test_kind_detection():
    assert kind_of("a.PNG") == "image"
    assert kind_of("b.mp4") == "video"
    assert kind_of("c.MP3") == "audio"
    assert kind_of("d.pdf") == "pdf"
    assert kind_of("e.exe") is None


def test_actions_for_single_image():
    ids = {a.id for a in actions_for(["x.png"])}
    assert "img-to-webp" in ids and "imgs-to-pdf" in ids
    assert "pdf-merge" not in ids


def test_actions_for_two_pdfs_offers_merge():
    ids = {a.id for a in actions_for(["a.pdf", "b.pdf"])}
    assert "pdf-merge" in ids


def test_actions_for_one_pdf_hides_merge():
    ids = {a.id for a in actions_for(["a.pdf"])}
    assert "pdf-merge" not in ids and "pdf-split" in ids


def test_actions_for_mixed_kinds_is_empty():
    assert actions_for(["a.pdf", "b.png"]) == []
    assert actions_for(["a.exe"]) == []
    assert actions_for([]) == []


def test_every_handler_resolves():
    from grayson.core import ACTIONS, resolve_handler
    for a in ACTIONS:
        assert callable(resolve_handler(a.handler)), a.id


def test_unique_output(tmp_path):
    f = tmp_path / "photo.png"
    f.write_bytes(b"x")
    out1 = unique_output(f, "webp")
    assert out1.name == "photo-grayson.webp"
    out1.write_bytes(b"y")
    out2 = unique_output(f, "webp")
    assert out2.name == "photo-grayson-2.webp"
    out3 = unique_output(f)  # keep extension
    assert out3.name == "photo-grayson.png"


def test_slice_index_geometry():
    n = 6
    for i in range(n):
        mid = slice_mid_angle(i, n)
        # point at 60% radius along the slice's mid-angle (y down, 0 = north)
        dx, dy = 0.6 * math.sin(mid), -0.6 * math.cos(mid)
        assert slice_index(dx, dy, n) == i, f"slice {i}"


def test_slice_index_dead_zone_and_outside():
    assert slice_index(0, 0, 6) is None          # centre dismiss button
    assert slice_index(0.05, 0.05, 6) is None    # still dead zone
    assert slice_index(1.5, 0, 6) is None        # outside the ring
    assert slice_index(0.5, 0, 0) is None        # no slices


def test_slice_index_no_overlap_full_cover():
    # 800 random points inside the ring must each land in exactly one slice
    import random
    random.seed(7)
    for _ in range(800):
        r = random.uniform(0.23, 0.99)
        t = random.uniform(0, 2 * math.pi)
        dx, dy = r * math.sin(t), -r * math.cos(t)
        idx = slice_index(dx, dy, 8)
        assert idx is not None and 0 <= idx < 8
