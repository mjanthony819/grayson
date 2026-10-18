import pymupdf
import pytest

from grayson.cli import run_action


@pytest.fixture
def two_pdfs(tmp_path):
    paths = []
    for n in (2, 3):
        doc = pymupdf.open()
        for i in range(n):
            page = doc.new_page()
            page.insert_text((72, 72), f"doc {n} page {i + 1}")
        p = tmp_path / f"doc{n}.pdf"
        doc.save(p)
        doc.close()
        paths.append(p)
    return paths


def test_merge(two_pdfs):
    [out] = run_action("pdf-merge", two_pdfs)
    with pymupdf.open(out) as doc:
        assert doc.page_count == 5


def test_split_pages(two_pdfs):
    written = run_action("pdf-split", [two_pdfs[0]])
    assert len(written) == 2
    for w in written:
        with pymupdf.open(w) as doc:
            assert doc.page_count == 1


def test_compress(two_pdfs):
    [out] = run_action("pdf-compress", [two_pdfs[0]])
    assert out.exists() and out.stat().st_size > 0
    with pymupdf.open(out) as doc:
        assert doc.page_count == 2


def test_compress_with_big_image(tmp_path):
    from PIL import Image
    big = tmp_path / "big.png"
    Image.new("RGB", (3000, 2000), (10, 200, 90)).save(big)
    [pdf] = run_action("imgs-to-pdf", [big])
    before = pdf.stat().st_size
    [out] = run_action("pdf-compress", [pdf])
    assert out.stat().st_size < before  # 3000px image must have been downsampled


def test_pages_to_png(two_pdfs):
    written = run_action("pdf-to-png", [two_pdfs[1]])
    assert len(written) == 3
    from PIL import Image
    img = Image.open(written[0])
    assert img.width > 500  # 150 dpi render
