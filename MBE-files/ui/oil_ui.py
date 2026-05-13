from __future__ import annotations
from pathlib import Path
import importlib.util
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
	spec = importlib.util.spec_from_file_location(name, path)
	module = importlib.util.module_from_spec(spec)
	assert spec.loader is not None
	spec.loader.exec_module(module)
	return module


try:
	from calc import oil_mbe, pvt
	from utils.helpers import (
		calc_afactor_bo_rs,
		calc_afactor_bt,
		calc_cterm,
		calc_freq,
		calc_rhs_per_n,
	)
	calc_ce_simple = oil_mbe.calc_ce_simple
except Exception:
	oil_mbe = _load_module("oil_mbe", ROOT / "calc" / "oil_mbe.py")
	pvt = _load_module("pvt", ROOT / "calc" / "pvt.py")
	helpers = _load_module("helpers", ROOT / "utils" / "helpers.py")
	calc_afactor_bo_rs = helpers.calc_afactor_bo_rs
	calc_afactor_bt = helpers.calc_afactor_bt
	calc_cterm = helpers.calc_cterm
	calc_freq = helpers.calc_freq
	calc_rhs_per_n = helpers.calc_rhs_per_n
	calc_ce_simple = oil_mbe.calc_ce_simple


RESULT_KEY = "oil_result"


def _fmt(value: float, digits: int = 6) -> str:
	return f"{value:,.{digits}f}"


def _oil_target_options(drive_choice: str) -> list[str]:
	if drive_choice == "Undersaturated (Expansion)":
		return ["N", "Np", "dp", "Bo"]
	if drive_choice == "Solution Gas":
		return ["N", "Np", "Rp", "Bg", "Bt"]
	if drive_choice == "Gas Cap Drive":
		return ["N", "Np", "m", "Rp", "Bg", "Bgi", "Bt"]
	if drive_choice == "Water Drive":
		return ["N", "Np", "We", "Wp", "Rp", "Bg", "Bgi", "Bt"]
	return ["N", "We", "m", "Np", "Wp", "Rp", "Bg", "Bgi", "Bt", "dp"]


def _oil_label(target: str) -> str:
	labels = {
		"N": "Initial Oil-in-Place (N)",
		"Np": "Cumulative Oil Produced (Np)",
		"We": "Water Influx (We)",
		"Wp": "Cumulative Water Produced (Wp)",
		"m": "Gas Cap Ratio (m)",
		"dp": "Pressure Drop (delta P)",
		"Rp": "Cumulative Gas-Oil Ratio (Rp)",
		"Bg": "Gas FVF (Bg)",
		"Bgi": "Initial Gas FVF (Bgi)",
		"Bt": "Two-Phase FVF (Bt)",
		"Bo": "Oil FVF (Bo)",
	}
	return labels[target]


def _oil_style_box(title: str, body: str, accent: str = "#1e1e2e", text: str = "#cdd6f4") -> str:
	return f"""
	<div style="font-size: 15px; background-color: {accent}; padding: 15px; border-radius: 8px; color: {text}; border: 1px solid #45475a; margin-bottom: 10px;">
		{body}
	</div>
	"""


def _oil_render_summary(result: dict[str, float], pvt_mode: str, drive_choice: str) -> None:
	st.success(f"**Solved value:** {result['solved_label']} = {result['solved_value']:,.6f}")

	energy_body = f"""
	<p style="margin: 5px 0;"><b>Total Voidage (F):</b> {_fmt(result['withdrawal'])} rb</p>
	<p style="margin: 5px 0;"><b>Oil Expansion Energy (N·Eo):</b> {_fmt(result['n'] * result['eo'])} rb</p>
	<p style="margin: 5px 0;"><b>Gas Cap Energy (N·m·Eg):</b> {_fmt(result['n'] * result['m'] * result['eg'])} rb</p>
	<p style="margin: 5px 0;"><b>Net Water Influx:</b> {_fmt(result['we'] - result['wp'] * result['bw'])} rb</p>
	<p style="margin: 5px 0;"><b>Rock/Connate Water Energy (N·Efw):</b> {_fmt(result['n'] * result['efw'])} rb</p>
	"""
	st.markdown(_oil_style_box("Energy Terms", energy_body), unsafe_allow_html=True)

	dri_body = f"""
	<div style="display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
	    <span><b>DDI:</b> {_fmt(result['ddi'])}</span>
	    <span><b>SDI:</b> {_fmt(result['sdi'])}</span>
	    <span><b>WDI:</b> {_fmt(result['wdi'])}</span>
	    <span><b>EDI:</b> {_fmt(result['edi'])}</span>
	</div>
	<hr style="border-top: 1px solid #45475a; margin: 8px 0;">
	<b>SUM:</b> {_fmt(result['ddi'] + result['sdi'] + result['wdi'] + result['edi'])} (Must equal 1.0)
	"""
	st.markdown(_oil_style_box("Drive Indices", dri_body, text="#a6e3a1"), unsafe_allow_html=True)

	df = pd.DataFrame(
		{
			"Drive": ["Depletion", "Gas Cap", "Water", "Expansion"],
			"Index": [result["ddi"], result["sdi"], result["wdi"], result["edi"]],
		}
	)
	fig = px.pie(
		df[df["Index"] > 0],
		values="Index",
		names="Drive",
		hole=0.4,
		title="Drive Mechanism Distribution",
		color_discrete_sequence=px.colors.sequential.Teal,
	)
	st.plotly_chart(fig, width='stretch')

	if pvt_mode == "Use Bo & Rs" and drive_choice != "Undersaturated (Expansion)":
		swc = result["swi"]
		sg_formula = 1 - (1 - (result["np"] / result["n"])) * (result["bo"] / result["boi"]) * (1 - swc)
		method_1 = result["sg_balance"]
		method_2 = sg_formula
		# Render Free Gas Saturation HTML via components.html to ensure HTML tags display correctly
		html = _oil_style_box(
			"Free Gas Saturation",
			f"""
			<p style="margin: 5px 0;"><b>Method 1: Gas Balance Sg</b> = {_fmt(method_1, 4)} %</p>
			<p style="margin: 5px 0;"><b>Method 2: Handout Sg</b> = {_fmt(method_2, 4)} %</p>
			<p style="margin: 5px 0;"><b>Formula:</b> Sg = 1 - (1 - Np/N) · (Bo/Boi) · (1 - Swc)</p>
			""",
			accent="#1f2430",
		)
		components.html(html, height=140)

	st.divider()
	st.subheader("Havlena-Odeh Straight-Line Plot")
	fig_ho = go.Figure()
	fig_ho.add_trace(go.Scatter(x=[0, result["plot_x"]], y=[0, result["plot_y"]], mode="lines+markers", name="Trend", line=dict(color="orange", width=3)))
	fig_ho.update_layout(
		title=result["plot_title"],
		xaxis_title=result["plot_x_label"],
		yaxis_title=result["plot_y_label"],
		template="plotly_dark",
		hovermode="x unified",
	)
	st.plotly_chart(fig_ho, width='stretch')


def _oil_solve(values: dict[str, float], drive_choice: str, target: str, pvt_mode: str) -> dict[str, float]:
	use_bt = pvt_mode == "Use Bt (Two-Phase FVF)"
	bo = values.get("bo", 0.0)
	boi = values.get("boi", 0.0)
	rs = values.get("rs", 0.0)
	rsi = values.get("rsi", 0.0)
	bt = values.get("bt", 0.0)
	bti = values.get("bti", 0.0)
	bg = values.get("bg", 0.0)
	bgi = values.get("bgi", 0.0)
	np = values.get("np", 0.0)
	rp = values.get("rp", 0.0)
	wp = values.get("wp", 0.0)
	bw = values.get("bw", 1.0)
	we = values.get("we", 0.0)
	m = values.get("m", 0.0)
	swi = values.get("swi", 0.0)
	cw = values.get("cw", 0.0)
	cf = values.get("cf", 0.0)
	dp = values.get("dp", 0.0)
	inj_total = values.get("ginj", 0.0) * values.get("bginj", 0.0) + values.get("winj", 0.0) * values.get("bwi", 1.0)
	ce = calc_ce_simple(swi, cw, cf)
	cterm = calc_cterm(boi if not use_bt else bti, ce, dp)

	if use_bt:
		eo = oil_mbe.calc_eo_bt(bt, bti)
		eg = oil_mbe.calc_eg_bt(bti, bg, bgi)
		af = calc_afactor_bt(bt, rp, rsi, bg)
		current_fvf = bt
		initial_fvf = bti
	else:
		eo = oil_mbe.calc_eo(bo, boi, rs, rsi, bg)
		eg = oil_mbe.calc_eg(boi, bg, bgi)
		af = calc_afactor_bo_rs(bo, rp, rs, bg)
		current_fvf = bo
		initial_fvf = boi

	resolved = {
		"n": values.get("known_n", 0.0),
		"np": np,
		"rp": rp,
		"we": we,
		"wp": wp,
		"bo": bo,
		"boi": boi,
		"bt": bt,
		"bti": bti,
		"bg": bg,
		"bgi": bgi,
		"m": m,
		"eo": eo,
		"eg": eg,
		"efw": oil_mbe.calc_efw(initial_fvf, m, swi, cw, cf, dp),
		"afactor": af,
		"ce": ce,
		"cterm": cterm,
		"inj_total": inj_total,
		"bw": bw,
		"swi": swi,
		"gp": values.get("gp", 0.0),
	}

	f = calc_afactor_bo_rs(bo, rp, rs, bg) * np + wp * bw if not use_bt else calc_afactor_bt(bt, rp, rsi, bg) * np + wp * bw
	resolved["withdrawal"] = f
	resolved["net_water"] = we - wp * bw

	if target == "N":
		resolved["n"] = oil_mbe.solve_n(f, eo, eg, resolved["efw"], m, we, inj_total)
	elif target == "We":
		resolved["n"] = values["known_n"]
		resolved["we"] = oil_mbe.solve_we(f, resolved["n"], eo, eg, resolved["efw"], m, inj_total)
	elif target == "Np":
		resolved["n"] = values["known_n"]
		resolved["np"] = oil_mbe.solve_np(resolved["n"], eo, eg, resolved["efw"], m, we, wp, bw, af, inj_total)
	elif target == "Wp":
		resolved["n"] = values["known_n"]
		resolved["wp"] = oil_mbe.solve_wp(resolved["n"], eo, eg, resolved["efw"], m, we, np, af, bw, inj_total)
	elif target == "m":
		resolved["n"] = values["known_n"]
		rhs_per_n = calc_rhs_per_n(f, we, inj_total, resolved["n"])
		resolved["m"] = oil_mbe.solve_m(rhs_per_n, eo, eg, cterm)
	elif target == "dp":
		resolved["n"] = values["known_n"]
		rhs_per_n = calc_rhs_per_n(f, we, inj_total, resolved["n"])
		resolved["dp"] = oil_mbe.solve_dp(rhs_per_n, eo, eg, m, initial_fvf, ce)
	elif target == "Bo":
		resolved["n"] = values["known_n"]
		resolved["bo"] = oil_mbe.solve_bo(resolved["n"], np, boi, ce, dp)
	elif target == "Rp":
		resolved["n"] = values["known_n"]
		freq = calc_freq(resolved["n"], eo, eg, resolved["efw"], m, we, inj_total, wp, bw, np)
		resolved["rp"] = oil_mbe.solve_rp(freq, np, current_fvf, rs, bg, pvt_mode=pvt_mode, bt=bt, rsi=rsi)
	elif target == "Bg":
		resolved["n"] = values["known_n"]
		resolved["bg"] = oil_mbe.solve_bg(resolved["n"], np, bo, boi, rp, rs, rsi, bgi, m, we, wp, bw, resolved["efw"], inj_total=inj_total, pvt_mode=pvt_mode, bt=bt, bti=bti)
	elif target == "Bt":
		resolved["n"] = values["known_n"]
		resolved["bt"] = oil_mbe.solve_bt(resolved["n"], np, rp, rsi, bg, bti, m, eg, resolved["efw"], we, wp, bw, inj_total)
	elif target == "Bgi":
		resolved["n"] = values["known_n"]
		rhs_per_n = calc_rhs_per_n(f, we, inj_total, resolved["n"])
		resolved["bgi"] = oil_mbe.solve_bgi(resolved["n"], rhs_per_n, eo, resolved["efw"], m, boi if not use_bt else bti, bg)

	if target == "N":
		resolved["known_n"] = resolved["n"]
	else:
		resolved["known_n"] = values["known_n"]

	if pvt_mode == "Use Bo & Rs":
		current_fvf = resolved["bo"]
		initial_fvf = resolved["boi"]
		rs_value = rs
		rsi_value = rsi
	else:
		current_fvf = resolved["bt"]
		initial_fvf = resolved["bti"]
		rs_value = rs
		rsi_value = rsi

	if target == "N":
		f = calc_afactor_bo_rs(current_fvf, resolved["rp"], rs_value, bg) * np + wp * bw if not use_bt else calc_afactor_bt(current_fvf, resolved["rp"], rsi_value, bg) * np + wp * bw
		resolved["withdrawal"] = f
		resolved["net_water"] = we - wp * bw

	resolved["ddi"] = oil_mbe.calc_drive_indices(resolved["n"], eo, eg, resolved["efw"], m, we, wp, bw, resolved["withdrawal"])["ddi"]
	indices = oil_mbe.calc_drive_indices(resolved["n"], eo, eg, resolved["efw"], m, we, wp, bw, resolved["withdrawal"])
	resolved.update(indices)

	if drive_choice == "Undersaturated (Expansion)":
		plot_x = (eo + resolved["efw"])
		plot_y = resolved["withdrawal"]
		plot_title = "Havlena-Odeh Plot: Undersaturated Reservoir (Slope = N)"
		x_label = "Expansion Term (Eo + Efw)"
		y_label = "Total Withdrawal (F)"
	elif drive_choice == "Gas Cap Drive":
		denom_exp = eo + resolved["efw"]
		plot_x = eg / denom_exp if denom_exp > 0 else 0.0
		plot_y = resolved["withdrawal"] / denom_exp if denom_exp > 0 else 0.0
		plot_title = "Havlena-Odeh Plot: Gas Cap Drive"
		x_label = "Gas Cap Expansion / (Eo + Efw)"
		y_label = "Withdrawal / (Eo + Efw)"
	elif drive_choice == "Water Drive":
		plot_x = we / eo if eo > 0 else 0.0
		plot_y = resolved["withdrawal"] / eo if eo > 0 else 0.0
		plot_title = "Havlena-Odeh Plot: Water Drive"
		x_label = "Water Influx / Eo"
		y_label = "Withdrawal / Eo"
	else:
		plot_x = eo + m * eg + resolved["efw"]
		plot_y = resolved["withdrawal"] - we - inj_total
		plot_title = "Havlena-Odeh Plot: General Form"
		x_label = "Total Expansion Term (Eo + mEg + Efw)"
		y_label = "Net Withdrawal (F - We - Inj)"

	resolved["plot_x"] = plot_x
	resolved["plot_y"] = plot_y
	resolved["plot_title"] = plot_title
	resolved["plot_x_label"] = x_label
	resolved["plot_y_label"] = y_label

	if pvt_mode == "Use Bo & Rs" and drive_choice != "Undersaturated (Expansion)":
		pore_volume = (resolved["n"] * initial_fvf * (1 + m)) / (1 - swi) if swi != 1 else 0.0
		if pore_volume > 0:
			free_gas_remaining_scf = (resolved["n"] * rsi + resolved["n"] * m * boi / bgi if bgi > 0 else 0.0) - (np * resolved["rp"] if "rp" in resolved else np * rp) - ((resolved["n"] - np) * rs)
			free_gas_vol_rb = free_gas_remaining_scf * bg
			resolved["sg_balance"] = (free_gas_vol_rb / pore_volume) * 100
		else:
			resolved["sg_balance"] = 0.0
	else:
		resolved["sg_balance"] = 0.0

	if target == "Rp":
		resolved["solved_label"] = "Rp"
		resolved["solved_value"] = resolved["rp"]
	elif target == "Np":
		resolved["solved_label"] = "Np"
		resolved["solved_value"] = resolved["np"]
	elif target == "We":
		resolved["solved_label"] = "We"
		resolved["solved_value"] = resolved["we"]
	elif target == "Wp":
		resolved["solved_label"] = "Wp"
		resolved["solved_value"] = resolved["wp"]
	elif target == "m":
		resolved["solved_label"] = "m"
		resolved["solved_value"] = resolved["m"]
	elif target == "dp":
		resolved["solved_label"] = "delta P"
		resolved["solved_value"] = resolved["dp"]
	elif target == "Bo":
		resolved["solved_label"] = "Bo"
		resolved["solved_value"] = resolved["bo"]
	elif target == "Bg":
		resolved["solved_label"] = "Bg"
		resolved["solved_value"] = resolved["bg"]
	elif target == "Bt":
		resolved["solved_label"] = "Bt"
		resolved["solved_value"] = resolved["bt"]
	elif target == "Bgi":
		resolved["solved_label"] = "Bgi"
		resolved["solved_value"] = resolved["bgi"]
	else:
		resolved["solved_label"] = "N"
		resolved["solved_value"] = resolved["n"]

	return resolved


def render_oil_section() -> None:
	st.header("Oil Reservoir Analysis")

	with st.expander("🛢️ Volumetric OOIP Calculator (Handout Alternative)"):
		st.markdown("*Use this to calculate Initial Oil-in-Place (N) using reservoir volume rather than production data.*")
		c1, c2, c3, c4 = st.columns(4)
		v_bulk = c1.number_input("Reservoir Vol (acre-ft)", value=0.0, key="oil_vol_v")
		phi = c2.number_input("Porosity", value=0.0, format="%.4f", key="oil_vol_phi")
		swc = c3.number_input("Swc", value=0.0, format="%.4f", key="oil_vol_swc")
		boi_vol = c4.number_input("Boi [rb/STB]", value=1.0, format="%.5f", key="oil_vol_boi")
		if st.button("Calculate Volumetric N", key="oil_vol_btn"):
			try:
				st.success(f"**Volumetric OOIP (N):** {oil_mbe.calc_volumetric_ooip(v_bulk, phi, swc, boi_vol):,.2f} STB")
			except ValueError as exc:
				st.error(str(exc))

	st.divider()
		
	drive_mode = st.radio(
		"Do you know the drive mechanism?",
		["Yes (Shortcut Formulas)", "No (Diagnostic/General Form)"],
		horizontal=True,
		key="oil_drive_mode",
	)
	drive_choice = "Diagnostic/General Form"
	if drive_mode == "Yes (Shortcut Formulas)":
		drive_choice = st.selectbox(
			"Select Shortcut Formula:",
			["Undersaturated (Expansion)", "Solution Gas", "Gas Cap Drive", "Water Drive"],
			key="oil_drive_choice",
		)

	target_options = _oil_target_options(drive_choice)
	target = st.selectbox("What are we looking for?", [_oil_label(opt) for opt in target_options], key="oil_target_choice")
	target_key = next(key for key, value in {k: _oil_label(k) for k in target_options}.items() if value == target)

	if drive_choice == "Undersaturated (Expansion)":
		pvt_mode = "Use Bo & Rs"
	else:
		if target_key == "Bt":
			pvt_mode = "Use Bt (Two-Phase FVF)"
			st.info("PVT mode locked to Bt because Bt is the target variable.")
		else:
			pvt_mode = st.radio("PVT Data Input Mode:", ["Use Bo & Rs", "Use Bt (Two-Phase FVF)"], horizontal=True, key="oil_pvt_mode")

	m_override = None
	if drive_choice in ["Gas Cap Drive", "Diagnostic/General Form"] and target_key != "m":
		calc_m = st.checkbox("Calc m? (Gas Cap / Oil Vol)", key="oil_calc_m")
		if calc_m:
			m_cols = st.columns(2)
			with m_cols[0]:
				gas_cap_vol = st.number_input("Initial Gas Cap Vol", value=0.0, key="oil_gas_cap_vol")
			with m_cols[1]:
				oil_vol = st.number_input("Initial Oil Vol", value=1.0, key="oil_oil_vol")
			m_override = gas_cap_vol / oil_vol if oil_vol > 0 else 0.0
			st.info(f"Calculated m: {m_override:.6f}")

	rp_override = None
	if target_key != "Rp":
		calc_rp = st.checkbox("Calculate Rp? (Gp/Np)", key="oil_calc_rp")
		if calc_rp:
			rp_cols = st.columns(2)
			with rp_cols[0]:
				gp_value = st.number_input("Gp [SCF]", value=0.0, format="%.6f", key="oil_gp")
			with rp_cols[1]:
				np_for_rp = st.number_input("Np [STB]", value=0.0, format="%.6f", key="oil_np_for_rp")
			rp_override = gp_value / np_for_rp if np_for_rp > 0 else 0.0
			st.info(f"Calculated Rp: {rp_override:.6f}")

	dp_override = None
	if drive_choice in ["Undersaturated (Expansion)", "Diagnostic/General Form"] and target_key != "dp":
		calc_dp = st.checkbox("Calculate delta P from Pi and P?", key="oil_calc_dp")
		if calc_dp:
			dp_cols = st.columns(2)
			with dp_cols[0]:
				pi_val = st.number_input("Pi [psia]", value=0.0, key="oil_pi_for_dp")
			with dp_cols[1]:
				pc_val = st.number_input("Current P [psia]", value=0.0, key="oil_p_for_dp")
			dp_override = pi_val - pc_val
			st.info(f"Calculated delta P: {dp_override:,.2f} psi")

	bg_override = None
	if target_key != "Bg":
		calc_bg = st.checkbox("Calculate Bg & Eg from Z, T, P?", key="oil_calc_bg")
		if calc_bg:
			bg_cols = st.columns(3)
			with bg_cols[0]:
				z = st.number_input("Z factor", value=1.0, key="oil_z")
			with bg_cols[1]:
				t = st.number_input("T [R]", value=1.0, key="oil_t")
			with bg_cols[2]:
				p_val = st.number_input("P [psia]", value=1.0, key="oil_p")
			bg_override = pvt.calc_bg_from_pvt(z, t, p_val) if p_val > 0 and z > 0 and t > 0 else 0.0
			st.info(f"Calculated Bg: {bg_override:.6f} rb/SCF | Eg: {_fmt(pvt.calc_eg_from_pvt(z, t, p_val), 4)}")

	with st.form("oil_solver_form", clear_on_submit=False):
		st.subheader("Data Inputs")
		col1, col2, col3, col4 = st.columns(4)
		values: dict[str, float] = {}

		with col1:
			if target_key != "Np":
				values["np"] = st.number_input("Np [STB]", value=0.0, format="%.6f", key="oil_np")
			if target_key != "Rp":
				if rp_override is not None:
					values["rp"] = rp_override
				else:
					values["rp"] = st.number_input("Rp [SCF/STB]", value=0.0, format="%.6f", key="oil_rp")
			if m_override is not None:
				values["m"] = m_override
			values["rsi"] = st.number_input("Rsi [SCF/STB]", value=0.0, format="%.6f", key="oil_rsi")
			if drive_choice in ["Undersaturated (Expansion)", "Diagnostic/General Form"] and target_key != "dp":
				if dp_override is not None:
					values["dp"] = dp_override
				else:
					values["dp"] = st.number_input("delta P [psi]", value=0.0, format="%.6f", key="oil_dp")

		with col2:
			if pvt_mode == "Use Bo & Rs":
				if target_key != "Bo":
					values["bo"] = st.number_input("Bo [rb/STB]", value=0.0, format="%.6f", key="oil_bo")
				values["boi"] = st.number_input("Boi [rb/STB]", value=0.0, format="%.6f", key="oil_boi")
				if drive_choice != "Undersaturated (Expansion)" and target_key != "Rp":
					values["rs"] = st.number_input("Rs [SCF/STB]", value=0.0, format="%.6f", key="oil_rs")
			else:
				if target_key != "Bt":
					values["bt"] = st.number_input("Bt [rb/STB]", value=0.0, format="%.6f", key="oil_bt")
				values["bti"] = st.number_input("Bti [rb/STB]", value=0.0, format="%.6f", key="oil_bti")

			if target_key != "Bg":
				if bg_override is not None:
					values["bg"] = bg_override
				else:
					values["bg"] = st.number_input("Bg [rb/SCF]", value=0.0, format="%.6f", key="oil_bg")
			if target_key != "Bgi":
				values["bgi"] = st.number_input("Bgi [rb/SCF]", value=0.0, format="%.6f", key="oil_bgi")

		with col3:
			if drive_choice in ["Water Drive", "Diagnostic/General Form"]:
				if target_key != "Wp":
					values["wp"] = st.number_input("Wp [STB]", value=0.0, format="%.6f", key="oil_wp")
				values["bw"] = st.number_input("Bw [rb/STB]", value=1.0, format="%.6f", key="oil_bw")
			if drive_choice == "Diagnostic/General Form":
				values["ginj"] = st.number_input("Ginj [SCF]", value=0.0, format="%.6f", key="oil_ginj")
				values["bginj"] = st.number_input("Bginj [rb/SCF]", value=0.0, format="%.6f", key="oil_bginj")

		with col4:
			if drive_choice == "Diagnostic/General Form":
				values["winj"] = st.number_input("Winj [STB]", value=0.0, format="%.6f", key="oil_winj")
				values["bwi"] = st.number_input("Bwi [rb/STB]", value=1.0, format="%.6f", key="oil_bwi")
			if drive_choice in ["Undersaturated (Expansion)", "Diagnostic/General Form"]:
				values["swi"] = st.number_input("Swc / Swi", value=0.0, format="%.6f", key="oil_swi")
				values["cw"] = st.number_input("Cw [psi^-1]", value=0.0, format="%.8f", key="oil_cw")
				values["cf"] = st.number_input("Cf [psi^-1]", value=0.0, format="%.8f", key="oil_cf")

		st.divider()
		c_we, c_m = st.columns(2)
		with c_we:
			if drive_choice in ["Water Drive", "Diagnostic/General Form"] and target_key != "We":
				values["we"] = st.number_input("We [rb]", value=0.0, format="%.6f", key="oil_we")
		with c_m:
			if drive_choice in ["Gas Cap Drive", "Diagnostic/General Form"] and target_key != "m":
				if m_override is not None:
					values["m"] = m_override
				else:
					values["m"] = st.number_input("m [fraction]", value=0.0, format="%.6f", key="oil_m")

		if target_key != "N":
			values["known_n"] = st.number_input("**Enter known Initial Oil-in-Place (N) [STB]:**", value=0.0, format="%.6f", key="oil_known_n")

		submit = st.form_submit_button("Calculate Missing Variable", type="primary")

	if submit:
		try:
			result = _oil_solve(values, drive_choice, target_key, pvt_mode)
			st.session_state[RESULT_KEY] = result
		except ValueError as exc:
			st.session_state.pop(RESULT_KEY, None)
			st.error(str(exc))

	result = st.session_state.get(RESULT_KEY)
	if result:
		_oil_render_summary(result, pvt_mode, drive_choice)
