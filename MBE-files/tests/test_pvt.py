from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PVT_PATH = ROOT / "calc" / "pvt.py"


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


pvt = load_module(PVT_PATH)


def test_calc_bgi_from_pvt_uses_handout_constant() -> None:
    result = pvt.calc_bgi_from_pvt(0.85, 520, 3000)
    assert result == pytest.approx(0.02827 * 0.85 * 520 / 3000)


def test_calc_bg_from_pvt_matches_bgi_formula() -> None:
    result = pvt.calc_bg_from_pvt(0.87, 520, 2500)
    assert result == pytest.approx(0.02827 * 0.87 * 520 / 2500)


def test_calc_eg_from_pvt_matches_handout_constant() -> None:
    result = pvt.calc_eg_from_pvt(0.87, 520, 2500)
    assert result == pytest.approx(35.37 * 2500 / (0.87 * 520))


@pytest.mark.parametrize(
    "func_name,args",
    [
        ("calc_bgi_from_pvt", (0.0, 520, 3000)),
        ("calc_bgi_from_pvt", (0.85, 0.0, 3000)),
        ("calc_bgi_from_pvt", (0.85, 520, 0.0)),
        ("calc_bg_from_pvt", (0.0, 520, 2500)),
        ("calc_bg_from_pvt", (0.87, 0.0, 2500)),
        ("calc_bg_from_pvt", (0.87, 520, 0.0)),
        ("calc_eg_from_pvt", (0.0, 520, 2500)),
        ("calc_eg_from_pvt", (0.87, 0.0, 2500)),
        ("calc_eg_from_pvt", (0.87, 520, 0.0)),
    ],
)
def test_pvt_rejects_non_positive_inputs(func_name, args) -> None:
    with pytest.raises(ValueError):
        getattr(pvt, func_name)(*args)