"""hapax test suite - determinism is the whole product, so that's what we test."""
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import hapax  # noqa: E402


def test_determinism_same_seed_same_bytes():
    a = hapax.build_poster("a quiet machine")
    b = hapax.build_poster("a quiet machine")
    assert a == b


def test_seed_is_whitespace_sensitive():
    assert hapax.build_poster("a quiet machine") != hapax.build_poster("a quiet machine ")


def test_different_seeds_differ():
    assert hapax.build_poster("one") != hapax.build_poster("two")


def test_flags_change_output():
    base = hapax.build_poster("x")
    assert hapax.build_poster("x", grain=False) != base
    assert hapax.build_poster("x", caption=False) != base


@pytest.mark.parametrize("style", hapax.STYLE_NAMES)
def test_every_style_renders_valid_svg(style):
    svg = hapax.build_poster(f"probe {style}", style=style)
    assert svg.startswith('<?xml version="1.0"')
    assert svg.rstrip().endswith("</svg>")
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg


@pytest.mark.parametrize("palette", hapax.PALETTE_NAMES)
def test_every_palette_renders(palette):
    svg = hapax.build_poster("palette probe", palette=palette)
    assert "</svg>" in svg


def test_unknown_style_raises():
    with pytest.raises(ValueError):
        hapax.build_poster("x", style="nope")


def test_unknown_palette_raises():
    with pytest.raises(ValueError):
        hapax.build_poster("x", palette="nope")


def test_auto_resolves_to_known_names():
    for i in range(20):
        s = f"auto {i}"
        svg = hapax.build_poster(s)
        assert f"&quot;{s}&quot;" in svg  # caption is XML-escaped


def test_cli_smoke_and_byte_determinism(tmp_path):
    env = dict(os.environ, PYTHONPATH=os.path.join(os.path.dirname(__file__), ".."))
    out1 = tmp_path / "a.svg"
    out2 = tmp_path / "b.svg"
    for out in (out1, out2):
        subprocess.run(
            [sys.executable, os.path.join(
                os.path.dirname(__file__), "..", "hapax.py"),
             "cli probe seed", "-o", str(out), "--quiet"],
            check=True, env=env)
    assert out1.read_bytes() == out2.read_bytes()
    assert out1.stat().st_size > 1000


def test_sheet_mode(tmp_path):
    env = dict(os.environ, PYTHONPATH=os.path.join(os.path.dirname(__file__), ".."))
    folder = tmp_path / "sheet"
    subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "..", "hapax.py"),
         "sheet seed", "--sheet", "3", "-o", str(folder), "--quiet"],
        check=True, env=env)
    svgs = list(folder.glob("*.svg"))
    assert len(svgs) == 3
    assert len({p.read_bytes() for p in svgs}) == 3  # all distinct


def test_size_option(tmp_path):
    svg = hapax.build_poster("size probe", size=(800, 600))
    assert 'viewBox="0 0 800 600"' in svg
