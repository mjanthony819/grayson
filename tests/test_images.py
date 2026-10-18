import pytest
from PIL import Image

from grayson.cli import run_action


@pytest.fixture
def photo(tmp_path):
    p = tmp_path / "photo.png"
    img = Image.new("RGBA", (200, 100), (200, 30, 30, 255))
    for x in range(200):  # give it some detail so compression has work to do
        for y in range(0, 100, 7):
            img.putpixel((x, y), (x % 255, y % 255, 128, 255))
    img.save(p)
    return p


def test_convert_roundtrip(photo):
    [webp] = run_action("img-to-webp", [photo])
    assert webp.suffix == ".webp" and webp.exists()
    [jpg] = run_action("img-to-jpg", [webp])
    assert Image.open(jpg).format == "JPEG"  # RGBA source flattens fine
    [png] = run_action("img-to-png", [jpg])
    assert Image.open(png).format == "PNG"


def test_resize_half(photo):
    [out] = run_action("img-resize-50", [photo])
    assert Image.open(out).size == (100, 50)


def test_compress_shrinks(photo):
    [out] = run_action("img-compress", [photo])
    assert out.exists() and out.stat().st_size > 0
    assert Image.open(out).format == "PNG"


def test_grayscale(photo):
    [out] = run_action("img-grayscale", [photo])
    assert Image.open(out).mode in ("L", "LA")


def test_images_to_pdf(tmp_path):
    imgs = []
    for i, colour in enumerate(((255, 0, 0), (0, 255, 0), (0, 0, 255))):
        p = tmp_path / f"c{i}.png"
        Image.new("RGB", (50, 50), colour).save(p)
        imgs.append(p)
    [pdf] = run_action("imgs-to-pdf", imgs)
    assert pdf.suffix == ".pdf"
    import pymupdf
    with pymupdf.open(pdf) as doc:
        assert doc.page_count == 3
