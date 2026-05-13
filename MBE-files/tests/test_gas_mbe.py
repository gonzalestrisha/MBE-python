from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GAS_PATH = ROOT / "calc" / "gas_mbe.py"


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


gas_mbe = load_module(GAS_PATH)


def test_volumetric_giip_and_gp_match_handout_formulas() -> None:
    giip = gas_mbe.calc_volumetric_giip(100, 50, 0.20, 0.15, 0.004142866666666666)
    gp = gas_mbe.calc_gp_volumetric(100, 50, 0.20, 0.15, 0.004142866666666666, 0.010)

    hcpv = 43560 * 100 * 50 * 0.20 * (1 - 0.15)
    assert giip == pytest.approx(hcpv / 0.004142866666666666)
    assert gp == pytest.approx(hcpv * ((1 / 0.004142866666666666) - (1 / 0.010)))


def test_pz_and_g_from_pz() -> None:
    assert gas_mbe.calc_pz(2500, 0.87) == pytest.approx(2873.5632183908045)
    assert gas_mbe.calc_g_from_pz(3000, 0.85, 2500, 0.87, 1_000_000) == pytest.approx(
        (3000 / 0.85) * 1_000_000 / ((3000 / 0.85) - (2500 / 0.87))
    )


def test_general_gas_mbe_solvers_and_drive_indices() -> None:
    bg = 0.005102088
    bgi = 0.004142866666666666
    we = 50_000.0
    wp = 100_000.0
    bw = 1.0
    swi = 0.15
    cw = 3e-6
    cf = 4e-6
    dp = 500.0
    g_expected = 1_500_000.0
    gp = 1_000_000.0

    eg = gas_mbe.calc_eg_gas(bg, bgi)
    efw = gas_mbe.calc_efw_gas(bgi, swi, cw, cf, dp)
    f = g_expected * (eg + efw) + (we - wp * bw)
    g = gas_mbe.solve_g_general(gp, bg, bgi, we, wp, bw, swi, cw, cf, dp)

    assert eg == pytest.approx(bg - bgi)
    assert efw == pytest.approx(bgi * ((swi * cw + cf) / (1 - swi)) * dp)
    assert f == pytest.approx(g_expected * (eg + efw) + (we - wp * bw))
    assert g == pytest.approx((gp * bg - (we - wp * bw)) / (eg + efw))

    no_water = gas_mbe.solve_g_no_water(gp, bg, bgi)
    with_water = gas_mbe.solve_g_with_water(gp, bg, bgi, we, wp, bw)
    overpressured = gas_mbe.solve_g_overpressured(gp, bg, bgi, we, wp, bw, swi, cw, cf, dp)

    assert no_water == pytest.approx((gp * bg) / eg)
    assert with_water == pytest.approx((gp * bg - (we - wp * bw)) / eg)
    assert overpressured == pytest.approx(g)

    indices = gas_mbe.calc_drive_indices_gas(g_expected, eg, efw, we, wp, bw, f)
    assert indices["total"] == pytest.approx(1.0)
    assert indices["gei"] == pytest.approx((g_expected * eg) / f)
    assert indices["edi"] == pytest.approx((g_expected * efw) / f)
    assert indices["wdi"] == pytest.approx((we - wp * bw) / f)


def test_reverse_solvers_and_validation_guards() -> None:
    bg = 0.005102088
    bgi = 0.004142866666666666
    g = 1_500_000.0
    gp = 1_000_000.0
    we = 50_000.0
    wp = 100_000.0
    bw = 1.0
    swi = 0.15
    cw = 3e-6
    cf = 4e-6
    dp = 500.0

    solved_we = gas_mbe.solve_we_gas(gp, bg, bgi, g, wp, bw, swi, cw, cf, dp)
    solved_gp = gas_mbe.solve_gp_gas(g, bg, bgi, we, wp, bw, swi, cw, cf, dp)
    solved_wp = gas_mbe.solve_wp_gas(g, gp, bg, bgi, we, bw, swi, cw, cf, dp)

    assert solved_we == pytest.approx(
        gas_mbe.calc_f_gas(gp, bg, wp, bw)
        - g * (gas_mbe.calc_eg_gas(bg, bgi) + gas_mbe.calc_efw_gas(bgi, swi, cw, cf, dp))
    )
    assert solved_gp == pytest.approx(
        (g * (gas_mbe.calc_eg_gas(bg, bgi) + gas_mbe.calc_efw_gas(bgi, swi, cw, cf, dp)) + we - wp * bw) / bg
    )
    assert solved_wp == pytest.approx(
        (g * (gas_mbe.calc_eg_gas(bg, bgi) + gas_mbe.calc_efw_gas(bgi, swi, cw, cf, dp)) + we - gp * bg) / bw
    )

    with pytest.raises(ValueError):
        gas_mbe.calc_volumetric_giip(100, 50, 0.20, 1.0, bgi)
    with pytest.raises(ValueError):
        gas_mbe.calc_gp_volumetric(100, 50, 0.20, 0.15, 0.0, 0.01)
    with pytest.raises(ValueError):
        gas_mbe.calc_pz(0.0, 0.87)
    with pytest.raises(ValueError):
        gas_mbe.calc_drive_indices_gas(g, 0.0, 0.0, we, wp, bw, 0.0)