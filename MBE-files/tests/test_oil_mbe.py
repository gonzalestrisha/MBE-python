from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CALC_PATH = ROOT / "calc"
UTILS_PATH = ROOT / "utils"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(CALC_PATH) not in sys.path:
    sys.path.insert(0, str(CALC_PATH))
if str(UTILS_PATH) not in sys.path:
    sys.path.insert(0, str(UTILS_PATH))


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


oil_mbe = load_module(CALC_PATH / "oil_mbe.py")


def test_calc_volumetric_ooip_matches_handout_formula() -> None:
    result = oil_mbe.calc_volumetric_ooip(1000, 0.20, 0.15, 1.2)
    assert result == pytest.approx(7758 * 1000 * 0.20 * (1 - 0.15) / 1.2)


def test_calculate_expansion_and_withdrawal_terms() -> None:
    eo = oil_mbe.calc_eo(1.15, 1.2, 600, 700, 0.005102088)
    eg = oil_mbe.calc_eg(1.2, 0.005102088, 0.004142866666666666)
    efw = oil_mbe.calc_efw(1.2, 0.25, 0.15, 3e-6, 4e-6, 500)
    f = oil_mbe.calc_withdrawal(500_000, 1.15, 800, 600, 0.005102088, 100_000, 1.0)

    assert eo == pytest.approx((1.15 - 1.2) + (700 - 600) * 0.005102088)
    assert eg == pytest.approx(1.2 * ((0.005102088 / 0.004142866666666666) - 1))
    assert efw == pytest.approx(1.2 * (1 + 0.25) * ((0.15 * 3e-6 + 4e-6) / (1 - 0.15)) * 500)
    assert f == pytest.approx(500_000 * (1.15 + (800 - 600) * 0.005102088) + 100_000)


def test_solve_n_and_we_round_trip() -> None:
    n_expected = 1_064_000.0
    eo = oil_mbe.calc_eo(1.15, 1.2, 600, 700, 0.005102088)
    eg = oil_mbe.calc_eg(1.2, 0.005102088, 0.004142866666666666)
    efw = oil_mbe.calc_efw(1.2, 0.25, 0.15, 3e-6, 4e-6, 500)
    we_expected = 50_000.0
    f = n_expected * (eo + 0.25 * eg + efw) + we_expected
    n = oil_mbe.solve_n(f, eo, eg, efw, 0.25, we_expected)
    we = oil_mbe.solve_we(f, n_expected, eo, eg, efw, 0.25)

    assert n == pytest.approx(n_expected)
    assert we == pytest.approx(we_expected)


def test_solve_m_and_drive_indices() -> None:
    n = 1_064_000.0
    eo = oil_mbe.calc_eo(1.15, 1.2, 600, 700, 0.005102088)
    eg = oil_mbe.calc_eg(1.2, 0.005102088, 0.004142866666666666)
    efw = oil_mbe.calc_efw(1.2, 0.25, 0.15, 3e-6, 4e-6, 500)
    bw = 1.0
    we = 50_000.0
    wp = 100_000.0
    m = 0.25
    ce = oil_mbe.calc_ce_simple(0.15, 3e-6, 4e-6)
    cterm = 1.2 * ce * 500
    f = n * (eo + m * eg + efw) + we
    f_total = f - wp * bw
    rhs_per_n = (f - we) / n

    solved_m = oil_mbe.solve_m(rhs_per_n, eo, eg, cterm)
    indices = oil_mbe.calc_drive_indices(n, eo, eg, efw, m, we, wp, bw, f_total)

    raw_ddi = max(0.0, (n * eo) / f_total)
    raw_sdi = max(0.0, (n * m * eg) / f_total)
    raw_wdi = max(0.0, (we - wp * bw) / f_total)
    raw_edi = max(0.0, (n * efw) / f_total)
    raw_total = raw_ddi + raw_sdi + raw_wdi + raw_edi

    assert solved_m == pytest.approx(0.25)
    assert indices["total"] == pytest.approx(indices["ddi"] + indices["sdi"] + indices["edi"] + indices["wdi"])
    assert indices["ddi"] == pytest.approx(raw_ddi / raw_total)
    assert indices["sdi"] == pytest.approx(raw_sdi / raw_total)
    assert indices["wdi"] == pytest.approx(raw_wdi / raw_total)
    assert indices["edi"] == pytest.approx(raw_edi / raw_total)


def test_solve_rp_and_validation_guards() -> None:
    rp = oil_mbe.solve_rp(12.0, 500_000, 1.15, 600, 0.005102088)
    assert rp == pytest.approx((12.0 - 1.15) / 0.005102088 + 600)

    with pytest.raises(ValueError):
        oil_mbe.solve_rp(12.0, 500_000, 1.15, 600, 0.0)

    with pytest.raises(ValueError):
        oil_mbe.calc_eg(1.2, 0.005, 0.0)

    with pytest.raises(ValueError):
        oil_mbe.calc_drive_indices(1.0, 0.1, 0.2, 0.3, 0.25, 0.0, 0.0, 1.0, 0.0)


def test_drive_indices_are_normalized_when_water_term_is_negative() -> None:
    indices = oil_mbe.calc_drive_indices(100.0, 1.0, 2.0, 1.0, 1.0, 0.0, 100.0, 1.0, 100.0)

    assert indices["wdi"] == pytest.approx(0.0)
    assert indices["ddi"] == pytest.approx(0.25)
    assert indices["sdi"] == pytest.approx(0.50)
    assert indices["edi"] == pytest.approx(0.25)
    assert indices["total"] == pytest.approx(1.0)