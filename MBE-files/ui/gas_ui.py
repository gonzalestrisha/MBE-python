from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
RESULT_KEY = "gas_result"


def _load_module(name: str, path: Path):
	spec = importlib.util.spec_from_file_location(name, path)
	module = importlib.util.module_from_spec(spec)
	assert spec.loader is not None
	spec.loader.exec_module(module)
	return module


try:
	from calc import gas_mbe, pvt
except Exception:
	gas_mbe = _load_module("gas_mbe", ROOT / "calc" / "gas_mbe.py")
	pvt = _load_module("pvt", ROOT / "calc" / "pvt.py")


def _fmt(value: float, digits: int = 6) -> str:
	return f"{value:,.{digits}f}"


def _style_box(body: str, accent: str = "#1e1e2e", text: str = "#cdd6f4") -> str:
	return f"""
	<div style="font-size: 15px; background-color: {accent}; padding: 15px; border-radius: 8px; color: {text}; border: 1px solid #45475a; margin-bottom: 10px;">
		{body}
	</div>
	"""


def _gas_pvt_fields(prefix: str, label: str) -> tuple[float, float, float]:
	st.caption(label)
	z = st.number_input(f"{prefix} Z", value=0.85, format="%.6f")
	t = st.number_input(f"{prefix} T (R)", value=660.0, format="%.2f")
	p = st.number_input(f"{prefix} P (psia)", value=3000.0, format="%.2f")
	return z, t, p


def _resolve_bg(use_pvt_bg: bool) -> float:
	if not use_pvt_bg:
		return st.number_input("Bg (rb/SCF)", value=0.0045, format="%.6f")

	st.caption("Compute Bg from Z/T/P")
	z, t, p = _gas_pvt_fields("Bg", "Bg PVT inputs")
	return pvt.calc_bg_from_pvt(z, t, p)


def _solve_gas_result(values: dict[str, float], target: str, complexity: str, use_pvt_bg: bool) -> dict[str, float]:
	bg = values["bg"]
	bgi = values["bgi"]
	gp = values.get("gp", 0.0)
	we = values.get("we", 0.0)
	wp = values.get("wp", 0.0)
	bw = values.get("bw", 1.0)
	swi = values.get("swi", 0.0)
	cw = values.get("cw", 0.0)
	cf = values.get("cf", 0.0)
	dp = values.get("dp", 0.0)
	known_g = values.get("known_g", 0.0)

	if complexity == "Volumetric (Expansion Only)":
		eg = gas_mbe.calc_eg_gas(bg, bgi)
		efw = 0.0
	else:
		eg = gas_mbe.calc_eg_gas(bg, bgi)
		efw = gas_mbe.calc_efw_gas(bgi, swi, cw, cf, dp)

	f = gas_mbe.calc_f_gas(gp, bg, wp, bw)

	result = {
		"bg": bg,
		"bgi": bgi,
		"gp": gp,
		"we": we,
		"wp": wp,
		"bw": bw,
		"swi": swi,
		"cw": cw,
		"cf": cf,
		"dp": dp,
		"known_g": known_g,
		"plot_pi": values.get("plot_pi", 0.0),
		"plot_zi": values.get("plot_zi", 0.0),
		"plot_gp": values.get("plot_gp", 0.0),
		"plot_p": values.get("plot_p", 0.0),
		"plot_z": values.get("plot_z", 0.0),
		"eg": eg,
		"efw": efw,
		"f": f,
		"use_pvt_bg": use_pvt_bg,
	}

	if target == "G":
		if complexity == "Volumetric (Expansion Only)":
			g = gas_mbe.solve_g_no_water(gp, bg, bgi)
		elif complexity == "Water Drive":
			g = gas_mbe.solve_g_with_water(gp, bg, bgi, we, wp, bw)
		else:
			g = gas_mbe.solve_g_overpressured(gp, bg, bgi, we, wp, bw, swi, cw, cf, dp)
		result["g"] = g
		result["solved_label"] = "G"
		result["solved_value"] = g
		result["gp_solved"] = gp
		result["we_solved"] = we
		result["wp_solved"] = wp
	elif target == "We":
		g = known_g
		if complexity == "Volumetric (Expansion Only)":
			we = gas_mbe.solve_we_gas(gp, bg, bgi, g, wp, bw)
		elif complexity == "Water Drive":
			we = gas_mbe.solve_we_gas(gp, bg, bgi, g, wp, bw)
		else:
			we = gas_mbe.solve_we_gas(gp, bg, bgi, g, wp, bw, swi, cw, cf, dp)
		result.update({"g": g, "we": we, "solved_label": "We", "solved_value": we, "we_solved": we, "gp_solved": gp, "wp_solved": wp})
	elif target == "Gp":
		g = known_g
		if complexity == "Volumetric (Expansion Only)":
			gp = gas_mbe.solve_gp_gas(g, bg, bgi, we, wp, bw)
		elif complexity == "Water Drive":
			gp = gas_mbe.solve_gp_gas(g, bg, bgi, we, wp, bw)
		else:
			gp = gas_mbe.solve_gp_gas(g, bg, bgi, we, wp, bw, swi, cw, cf, dp)
		result.update({"g": g, "gp": gp, "solved_label": "Gp", "solved_value": gp, "gp_solved": gp, "we_solved": we, "wp_solved": wp})
	else:
		g = known_g
		if bw == 0:
			raise ValueError("Bw cannot be zero when solving for Wp.")
		if complexity == "Volumetric (Expansion Only)":
			wp = gas_mbe.solve_wp_gas(g, gp, bg, bgi, we, bw)
		elif complexity == "Water Drive":
			wp = gas_mbe.solve_wp_gas(g, gp, bg, bgi, we, bw)
		else:
			wp = gas_mbe.solve_wp_gas(g, gp, bg, bgi, we, bw, swi, cw, cf, dp)
		result.update({"g": g, "wp": wp, "solved_label": "Wp", "solved_value": wp, "gp_solved": gp, "we_solved": we, "wp_solved": wp})

	gp_used = result.get("gp_solved", gp)
	we_used = result.get("we_solved", we)
	wp_used = result.get("wp_solved", wp)
	g_used = result.get("g", known_g if target != "G" else result["g"])
	f_used = gas_mbe.calc_f_gas(gp_used, bg, wp_used, bw)
	# calc_drive_indices_gas raises when F == 0. Handle gracefully so UI doesn't error.
	try:
		drive = gas_mbe.calc_drive_indices_gas(g_used, eg, efw, we_used, wp_used, bw, f_used)
		gei = drive["gei"]
		edi = drive["edi"]
		wdi = drive["wdi"]
		drive_total = drive["total"]
		drive_error = None
	except ValueError as exc:
		gei = 0.0
		edi = 0.0
		wdi = 0.0
		drive_total = 0.0
		drive_error = str(exc)

	result.update(
		{
			"g": g_used,
			"gp_solved": gp_used,
			"we_solved": we_used,
			"wp_solved": wp_used,
			"f": f_used,
			"gei": gei,
			"edi": edi,
			"wdi": wdi,
			"drive_total": drive_total,
			"net_water": we_used - wp_used * bw,
			"drive_error": drive_error,
		}
	)
	return result


def _render_results(result: dict[str, float], complexity: str, target: str) -> None:
	st.success(f"Solved {result['solved_label']}: {_fmt(result['solved_value'])}")

	energy_body = f"""
	<p style="margin: 5px 0;"><b>F:</b> {_fmt(result.get('f', 0.0))} rb</p>
	<p style="margin: 5px 0;"><b>G*Eg:</b> {_fmt(result.get('g', 0.0) * result.get('eg', 0.0))} rb</p>
	<p style="margin: 5px 0;"><b>G*Efw:</b> {_fmt(result.get('g', 0.0) * result.get('efw', 0.0))} rb</p>
	<p style="margin: 5px 0;"><b>Net water:</b> {_fmt(result.get('net_water', 0.0))} rb</p>
	"""
	st.markdown(_style_box(energy_body), unsafe_allow_html=True)

	# If drive indices calculation failed (F == 0), show a friendly warning and skip the pie.
	if result.get("drive_error"):
		st.warning(result.get("drive_error"))
	else:
		drive_body = f"""
		<div style="display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
			<span><b>GEI:</b> {_fmt(result.get('gei', 0.0))}</span>
			<span><b>EDI:</b> {_fmt(result.get('edi', 0.0))}</span>
			<span><b>WDI:</b> {_fmt(result.get('wdi', 0.0))}</span>
		</div>
		<hr style="border-top: 1px solid #45475a; margin: 8px 0;">
		<b>SUM:</b> {_fmt(result.get('drive_total', 0.0))} (Must equal 1.0)
		"""
		st.markdown(_style_box(drive_body, text="#a6e3a1"), unsafe_allow_html=True)

		pie_df = pd.DataFrame(
			{
				"Drive": ["GEI", "EDI", "WDI"],
				"Index": [result.get("gei", 0.0), result.get("edi", 0.0), result.get("wdi", 0.0)],
			}
		)
		fig = px.pie(
			pie_df[pie_df["Index"] > 0],
			values="Index",
			names="Drive",
			hole=0.4,
			title="Drive Mechanism Distribution",
			color_discrete_sequence=px.colors.sequential.Teal,
		)
		st.plotly_chart(fig, width='stretch')

	if complexity == "Volumetric (Expansion Only)":
		st.subheader("p/z Plot")
		plot_pi = result["plot_pi"]
		plot_zi = result["plot_zi"]
		plot_p = result["plot_p"]
		plot_z = result["plot_z"]
		plot_gp = result["plot_gp"]
		pz = gas_mbe.calc_pz(plot_p, plot_z)
		g_from_pz = gas_mbe.calc_g_from_pz(plot_pi, plot_zi, plot_p, plot_z, plot_gp)
		fig_pz = go.Figure()
		fig_pz.add_trace(
			go.Scatter(
				x=[0, plot_gp, g_from_pz],
				y=[plot_pi / plot_zi, pz, 0],
				mode="lines+markers",
				name="p/z trend",
				line=dict(color="orange", width=3),
			)
		)
		fig_pz.update_layout(
			title="p/z Straight-Line Plot",
			xaxis_title="Gp (SCF)",
			yaxis_title="p/z",
			template="plotly_dark",
			hovermode="x unified",
		)
		st.plotly_chart(fig_pz, width='stretch')

	if complexity == "Water Drive":
		st.subheader("Havlena-Odeh Plot")
		fig_ho = go.Figure()
		x = result["we_solved"] / result["eg"] if result["eg"] != 0 else 0.0
		y = result["f"] / result["eg"] if result["eg"] != 0 else 0.0
		fig_ho.add_trace(
			go.Scatter(
				x=[0, x],
				y=[result["g"], y],
				mode="lines+markers",
				name="F/Eg vs We/Eg",
				line=dict(color="cyan", width=3),
			)
		)
		fig_ho.update_layout(
			title="Water Drive Havlena-Odeh Plot",
			xaxis_title="We / Eg",
			yaxis_title="F / Eg",
			template="plotly_dark",
			hovermode="x unified",
		)
		st.plotly_chart(fig_ho, width='stretch')

	if complexity == "General Form (Overpressured - includes Efw)":
		st.subheader("Havlena-Odeh Plot")
		fig_ho = go.Figure()
		x = result["eg"] + result["efw"]
		y = result["f"] - result["we_solved"]
		fig_ho.add_trace(
			go.Scatter(
				x=[0, x],
				y=[0, y],
				mode="lines+markers",
				name="F-We vs Eg+Efw",
				line=dict(color="cyan", width=3),
			)
		)
		fig_ho.update_layout(
			title="General Form Havlena-Odeh Plot",
			xaxis_title="Eg + Efw",
			yaxis_title="F - We",
			template="plotly_dark",
			hovermode="x unified",
		)
		st.plotly_chart(fig_ho, width='stretch')


def render_gas_section() -> None:
	st.header("Gas Reservoir")
	st.markdown("Gas material balance workflows, PVT helpers, and straight-line diagnostics.")

	with st.expander("Volumetric GIIP", expanded=False):
		area = st.number_input("Area (acres)", value=1000.0, format="%.2f")
		h = st.number_input("h (ft)", value=50.0, format="%.2f")
		phi = st.number_input("phi", value=0.20, format="%.4f")
		swi = st.number_input("Swi", value=0.25, format="%.4f")
		bgi = st.number_input("Bgi (rb/SCF)", value=0.0050, format="%.6f")
		if st.button("Calculate GIIP"):
			g = gas_mbe.calc_volumetric_giip(area, h, phi, swi, bgi)
			st.success(f"Volumetric GIIP: {_fmt(g)} SCF")

	target = st.selectbox("Target variable", ["G", "We", "Gp", "Wp"])
	complexity = st.selectbox(
		"Complexity",
		[
			"Volumetric (Expansion Only)",
			"Water Drive",
			"General Form (Overpressured - includes Efw)",
		],
	)

	if complexity == "Volumetric (Expansion Only)":
		st.info("Volumetric mode uses Bg and Bgi only for the MBE solve; p/z is shown separately below.")

	use_bg_pvt = st.checkbox("Calculate Bg from Z/T/P", value=False)
	use_delta_pressure = st.checkbox("Calculate delta P from Pi/P", value=False)

	with st.form("gas_solver_form"):
		col1, col2 = st.columns(2)

		with col1:
			gp = 0.0
			if target != "G":
				gp = st.number_input("Gp (SCF)", value=50000.0, format="%.2f")

			if use_bg_pvt:
				bg_z = st.number_input("Bg Z", value=0.85, format="%.6f")
				bg_t = st.number_input("Bg T (R)", value=660.0, format="%.2f")
				bg_p = st.number_input("Bg P (psia)", value=3000.0, format="%.2f")
				bg = pvt.calc_bg_from_pvt(bg_z, bg_t, bg_p)
			else:
				bg = st.number_input("Bg (rb/SCF)", value=0.0050, format="%.6f")

			bgi = st.number_input("Bgi (rb/SCF)", value=0.0045, format="%.6f")
			known_g = 0.0
			if target != "G":
				known_g = st.number_input("Known G (SCF)", value=100000000.0, format="%.2f")

		with col2:
			bw = st.number_input("Bw (rb/STB)", value=1.0, format="%.6f")
			wp = 0.0
			if target != "Wp" and complexity != "Volumetric (Expansion Only)":
				wp = st.number_input("Wp (STB)", value=0.0, format="%.2f")

			we = 0.0
			if target != "We" and complexity != "Volumetric (Expansion Only)":
				we = st.number_input("We (rb)", value=0.0, format="%.2f")

			swi_drive = 0.0
			cw = 0.0
			cf = 0.0
			dp = 0.0
			if complexity == "General Form (Overpressured - includes Efw)":
				swi_drive = st.number_input("Swi", value=0.25, format="%.4f")
				cw = st.number_input("cw (1/psi)", value=0.000003, format="%.9f")
				cf = st.number_input("cf (1/psi)", value=0.000010, format="%.9f")
				if use_delta_pressure:
					pi = st.number_input("Pi (psia)", value=3500.0, format="%.2f")
					p = st.number_input("P (psia)", value=3000.0, format="%.2f")
					dp = pi - p
					st.caption(f"delta P = { _fmt(dp, 3) } psi")
				else:
					dp = st.number_input("delta P (psi)", value=500.0, format="%.2f")
			else:
				st.caption("delta P is not required unless General Form is selected.")

		if complexity == "Volumetric (Expansion Only)":
			st.markdown("#### p/z Plot Inputs")
			plot_col1, plot_col2 = st.columns(2)
			with plot_col1:
				plot_pi = st.number_input("pi (psia)", value=3500.0, format="%.2f")
				plot_zi = st.number_input("zi", value=0.95, format="%.6f")
				plot_gp = st.number_input("Gp for plot (SCF)", value=50000.0, format="%.2f")
			with plot_col2:
				plot_p = st.number_input("Current p (psia)", value=3000.0, format="%.2f")
				plot_z = st.number_input("Current z", value=0.90, format="%.6f")
		else:
			plot_pi = 0.0
			plot_zi = 0.0
			plot_gp = 0.0
			plot_p = 0.0
			plot_z = 0.0

		submit = st.form_submit_button("Calculate")

	if submit:
		try:
			values = {
				"gp": gp,
				"bg": bg,
				"bgi": bgi,
				"bw": bw,
				"wp": wp,
				"we": we,
				"swi": swi_drive,
				"cw": cw,
				"cf": cf,
				"dp": dp,
				"known_g": known_g,
				"plot_pi": plot_pi,
				"plot_zi": plot_zi,
				"plot_gp": plot_gp,
				"plot_p": plot_p,
				"plot_z": plot_z,
			}
			result = _solve_gas_result(values, target, complexity, use_bg_pvt)
			st.session_state[RESULT_KEY] = result
		except Exception as exc:
			st.error(str(exc))

	if RESULT_KEY in st.session_state:
		_render_results(st.session_state[RESULT_KEY], complexity, target)
