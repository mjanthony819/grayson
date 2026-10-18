from PIL import Image

from grayson.cli import main


def test_list_actions(capsys):
    assert main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "img-to-webp" in out and "pdf-merge" in out


def test_cli_end_to_end(tmp_path, capsys):
    photo = tmp_path / "shot.png"
    Image.new("RGB", (80, 60), (1, 2, 3)).save(photo)
    assert main([str(photo), "--action", "img-to-jpg"]) == 0
    printed = capsys.readouterr().out.strip()
    assert printed.endswith("shot-grayson.jpg")


def test_cli_rejects_wrong_action(tmp_path):
    photo = tmp_path / "shot.png"
    Image.new("RGB", (10, 10)).save(photo)
    try:
        main([str(photo), "--action", "pdf-merge"])
    except SystemExit as e:
        assert e.code != 0
    else:
        raise AssertionError("should have exited")
