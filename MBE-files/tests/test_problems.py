from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))


def load_module(path: Path):
	spec = importlib.util.spec_from_file_location(path.stem, path)
	module = importlib.util.module_from_spec(spec)
	assert spec.loader is not None
	spec.loader.exec_module(module)
	return module


oil_mbe = load_module(ROOT / "calc" / "oil_mbe.py")
gas_mbe = load_module(ROOT / "calc" / "gas_mbe.py")


def fmt_answer(value: float, positive_digits: int = 2, negative_digits: int = 4) -> str:
	"""Format answers with finer precision for negative values."""
	return f"{value:,.{negative_digits}f}" if value < 0 else f"{value:,.{positive_digits}f}"


def solve_problem1(
	*,
	n_mmstb: float,
	m: float,
	pi: float,
	p: float,
	boi: float,
	bt_initial: float,
	bt_current: float,
	rsi: float,
	bg_initial: float,
	rs_current: float,
	bg_current: float,
	oil_produced_mmstb: float,
	gas_produced_mmmscf: float,
	water_produced_stb: float,
	bw: float,
	swi: float,
	cw: float,
	cf: float,
) -> dict[str, float]:
	n = n_mmstb * 1_000_000.0
	np_prod = oil_produced_mmstb * 1_000_000.0
	rp = gas_produced_mmmscf / oil_produced_mmstb
	dp = pi - p

	eo = oil_mbe.calc_eo_bt(bt_current, bt_initial)
	eg = oil_mbe.calc_eg_bt(bt_initial, bg_current, bg_initial)
	efw = oil_mbe.calc_efw(boi, m, swi, cw, cf, dp)
	withdrawal = oil_mbe.calc_withdrawal_bt(np_prod, bt_current, rp, rsi, bg_current, water_produced_stb, bw)
	we = oil_mbe.solve_we(withdrawal, n, eo, eg, efw, m)
	net_water_influx = we - water_produced_stb * bw
	net_withdrawal = withdrawal - water_produced_stb * bw
	indices = oil_mbe.calc_drive_indices(n, eo, eg, efw, m, we, water_produced_stb, bw, net_withdrawal)

	print("\nProblem 1 answers:")
	print(f"a. Cumulative water influx = {fmt_answer(we)} rb")
	print(f"b. Net water influx = {fmt_answer(net_water_influx)} rb")
	print("c. Primary driving indexes at 2,800 psi")
	print(f"   DDI = {fmt_answer(indices['ddi'], positive_digits=6)}")
	print(f"   SDI = {fmt_answer(indices['sdi'], positive_digits=6)}")
	print(f"   WDI = {fmt_answer(indices['wdi'], positive_digits=6)}")
	print(f"   EDI = {fmt_answer(indices['edi'], positive_digits=6)}")
	print(f"   Total = {fmt_answer(indices['total'], positive_digits=6)}")

	return {
		"eo": eo,
		"eg": eg,
		"efw": efw,
		"withdrawal": withdrawal,
		"we": we,
		"net_water_influx": net_water_influx,
		"net_withdrawal": net_withdrawal,
		"ddi": indices["ddi"],
		"sdi": indices["sdi"],
		"wdi": indices["wdi"],
		"edi": indices["edi"],
		"total": indices["total"],
	}


def solve_problem2(
	*,
	pi: float,
	p: float,
	bo_initial: float,
	bo_current: float,
	rs_initial: float,
	rs_current: float,
	np_mmstb: float,
	gp_mmmscf: float,
	bw: float,
	we_mmbbl: float,
	wp_mmbbl: float,
	bg_initial: float,
	bg_current: float,
	bulk_oil_zone_acft: float,
	bulk_gas_zone_acft: float,
) -> dict[str, float]:
	np = np_mmstb * 1_000_000.0
	gp = gp_mmmscf * 1_000_000_000.0
	we = we_mmbbl * 1_000_000.0
	wp = wp_mmbbl * 1_000_000.0
	m = bulk_gas_zone_acft / bulk_oil_zone_acft
	dp = pi - p
	rp = gp / np

	eo = (bo_initial - bo_current) + (rs_initial - rs_current) * bg_current
	eg = oil_mbe.calc_eg(bo_initial, bg_current, bg_initial)
	efw = oil_mbe.calc_efw(bo_initial, m, 0.0, 0.0, 0.0, dp)
	af = oil_mbe.calc_withdrawal(np, bo_current, rp, rs_current, bg_current, wp, bw)
	n = (np * bo_current + np * (rp - rs_current) * bg_current - (we - wp * bw)) / (eo + m * eg + efw)
	n_mmstb = n / 1_000_000.0
	indices = oil_mbe.calc_drive_indices(n, eo, eg, efw, m, we, wp, bw, af - wp * bw)

	print("\nProblem 2 answers:")
	print(f"a. Initial oil-in-place = {fmt_answer(n_mmstb, positive_digits=4)} MMSTB")
	print(f"   Initial oil-in-place = {fmt_answer(n, positive_digits=2)} STB")
	print(f"   Rp = {fmt_answer(rp, positive_digits=2)} scf/STB")
	print("   Supporting values:")
	print(f"   Eo = {fmt_answer(eo, positive_digits=6)}")
	print(f"   Eg = {fmt_answer(eg, positive_digits=6)}")
	print(f"   Efw = {fmt_answer(efw, positive_digits=6)}")
	print(f"   Withdrawal = {fmt_answer(af, positive_digits=2)} rb")
	print(f"   DDI = {fmt_answer(indices['ddi'], positive_digits=6)}")
	print(f"   SDI = {fmt_answer(indices['sdi'], positive_digits=6)}")
	print(f"   WDI = {fmt_answer(indices['wdi'], positive_digits=6)}")
	print(f"   EDI = {fmt_answer(indices['edi'], positive_digits=6)}")
	print(f"   Total = {fmt_answer(indices['total'], positive_digits=6)}")

	return {
		"n": n,
		"n_mmstb": n_mmstb,
		"rp": rp,
		"eo": eo,
		"eg": eg,
		"efw": efw,
		"af": af,
		"ddi": indices["ddi"],
		"gp_mmmscf": gp_mmmscf,
		"we": we,
		"wdi": indices["wdi"],
		"edi": indices["edi"],
		"total": indices["total"],
	}


def solve_problem3(
	*,
	initial_gas_mmscf: float,
	pi: float,
	p: float,
	bgi: float,
	bg: float,
) -> dict[str, float]:
	initial_gas = initial_gas_mmscf * 1_000_000.0
	gp = gas_mbe.solve_gp_gas(initial_gas, bg, bgi, 0.0, 0.0, 1.0)
	gp_mmmscf = gp / 1_000_000.0

	print("\nProblem 3 answers:")
	print(f"a. Gas produced = {fmt_answer(gp_mmmscf, positive_digits=4)} MMscf")
	print(f"   Gas produced = {fmt_answer(gp, positive_digits=2)} scf")
	print(f"   Input pressure drop = {fmt_answer(pi - p, positive_digits=2)} psi")
	print(f"   Bgi = {fmt_answer(bgi, positive_digits=6)} rb/SCF")
	print(f"   Bg = {fmt_answer(bg, positive_digits=6)} rb/SCF")

	return {
		"gp": gp,
		"gp_mmmscf": gp_mmmscf,
		"initial_gas": initial_gas,
	}


@pytest.mark.parametrize(
	(
		"n_mmstb",
		"m",
		"pi",
		"p",
		"boi",
		"bt_initial",
		"bt_current",
		"rsi",
		"bg_initial",
		"rs_current",
		"bg_current",
		"oil_produced_mmstb",
		"gas_produced_mmmscf",
		"water_produced_stb",
		"bw",
		"swi",
		"cw",
		"cf",
	),
	[
		(
			10.0,
			0.25,
			3000.0,
			2800.0,
			1.58,
			1.58,
			1.655,
			1040.0,
			0.00080,
			850.0,
			0.00092,
			1.0,
			1100.0,
			50_000.0,
			1.0,
			0.20,
			1.5e-6,
			1.0e-6,
		),
	],
)
def test_problem1(
	n_mmstb: float,
	m: float,
	pi: float,
	p: float,
	boi: float,
	bt_initial: float,
	bt_current: float,
	rsi: float,
	bg_initial: float,
	rs_current: float,
	bg_current: float,
	oil_produced_mmstb: float,
	gas_produced_mmmscf: float,
	water_produced_stb: float,
	bw: float,
	swi: float,
	cw: float,
	cf: float,
) -> None:
	n = n_mmstb * 1_000_000.0
	np_prod = oil_produced_mmstb * 1_000_000.0
	rp = gas_produced_mmmscf / oil_produced_mmstb
	dp = pi - p

	answers = solve_problem1(
		n_mmstb=n_mmstb,
		m=m,
		pi=pi,
		p=p,
		boi=boi,
		bt_initial=bt_initial,
		bt_current=bt_current,
		rsi=rsi,
		bg_initial=bg_initial,
		rs_current=rs_current,
		bg_current=bg_current,
		oil_produced_mmstb=oil_produced_mmstb,
		gas_produced_mmmscf=gas_produced_mmmscf,
		water_produced_stb=water_produced_stb,
		bw=bw,
		swi=swi,
		cw=cw,
		cf=cf,
	)

	assert answers["eo"] == pytest.approx(bt_current - bt_initial)
	assert answers["eg"] == pytest.approx(bt_initial * ((bg_current / bg_initial) - 1))
	assert answers["efw"] == pytest.approx(
		boi * (1 + m) * ((swi * cw + cf) / (1 - swi)) * dp
	)
	assert answers["withdrawal"] == pytest.approx(
		np_prod * (bt_current + (rp - rsi) * bg_current) + water_produced_stb * bw
	)
	assert answers["we"] == pytest.approx(411_281.25)
	assert answers["net_water_influx"] == pytest.approx(361_281.25)
	assert answers["ddi"] == pytest.approx((n * answers["eo"]) / answers["net_withdrawal"])
	assert answers["sdi"] == pytest.approx((n * m * answers["eg"]) / answers["net_withdrawal"])
	assert answers["wdi"] == pytest.approx(max(0.0, (answers["we"] - water_produced_stb * bw) / answers["net_withdrawal"]))
	assert answers["edi"] == pytest.approx((n * answers["efw"]) / answers["net_withdrawal"])
	assert answers["total"] == pytest.approx(1.0)


@pytest.mark.parametrize(
	(
		"pi",
		"p",
		"bo_initial",
		"bo_current",
		"rs_initial",
		"rs_current",
		"np_mmstb",
		"gp_mmmscf",
		"bw",
		"we_mmbbl",
		"wp_mmbbl",
		"bg_initial",
		"bg_current",
		"bulk_oil_zone_acft",
		"bulk_gas_zone_acft",
	),
	[
		(
			3000.0,
			2500.0,
			1.35,
			1.33,
			600.0,
			500.0,
			5.0,
			5.5,
			1.0,
			3.0,
			0.2,
			0.0011,
			0.0015,
			100_000.0,
			20_000.0,
		),
	],
)
def test_problem2(
	pi: float,
	p: float,
	bo_initial: float,
	bo_current: float,
	rs_initial: float,
	rs_current: float,
	np_mmstb: float,
		gp_mmmscf: float,
	bw: float,
	we_mmbbl: float,
	wp_mmbbl: float,
	bg_initial: float,
	bg_current: float,
	bulk_oil_zone_acft: float,
	bulk_gas_zone_acft: float,
) -> None:
	answers = solve_problem2(
		pi=pi,
		p=p,
		bo_initial=bo_initial,
		bo_current=bo_current,
		rs_initial=rs_initial,
		rs_current=rs_current,
		np_mmstb=np_mmstb,
			gp_mmmscf=gp_mmmscf,
		bw=bw,
		we_mmbbl=we_mmbbl,
		wp_mmbbl=wp_mmbbl,
		bg_initial=bg_initial,
		bg_current=bg_current,
		bulk_oil_zone_acft=bulk_oil_zone_acft,
		bulk_gas_zone_acft=bulk_gas_zone_acft,
	)

	assert answers["rp"] == pytest.approx(1100.0)
	assert answers["n_mmstb"] == pytest.approx(31.14, abs=0.01)
	assert answers["n"] == pytest.approx(31_140_000.0, abs=100_000.0)
	assert answers["total"] == pytest.approx(1.0)


@pytest.mark.parametrize(
	(
		"initial_gas_mmscf",
		"pi",
		"p",
		"bgi",
		"bg",
	),
	[
		(
			500.0,
			3000.0,
			2900.0,
			0.0010,
			0.0011,
		),
	],
)
def test_problem3(
	initial_gas_mmscf: float,
	pi: float,
	p: float,
	bgi: float,
	bg: float,
) -> None:
	answers = solve_problem3(
		initial_gas_mmscf=initial_gas_mmscf,
		pi=pi,
		p=p,
		bgi=bgi,
		bg=bg,
	)

	assert answers["gp_mmmscf"] == pytest.approx(45.4545454545, abs=0.0001)
	assert answers["gp"] == pytest.approx(45_454_545.4545, abs=1.0)
