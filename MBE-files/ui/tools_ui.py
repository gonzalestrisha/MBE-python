from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


try:
    from calc import gas_mbe, oil_mbe, pvt
except Exception:
    gas_mbe = _load_module("gas_mbe", ROOT / "calc" / "gas_mbe.py")
    oil_mbe = _load_module("oil_mbe", ROOT / "calc" / "oil_mbe.py")
    pvt = _load_module("pvt", ROOT / "calc" / "pvt.py")


def _fmt(value: float, digits: int = 6) -> str:
    return f"{value:,.{digits}f}"


def _style_box(body: str, accent: str = "#1e1e2e", text: str = "#cdd6f4") -> str:
    body = textwrap.dedent(body).strip()
    return f"""
<div style="font-size: 15px; background-color: {accent}; padding: 15px; border-radius: 8px; color: {text}; border: 1px solid #45475a;">
{body}
</div>
    """


def _render_volumetric_tab() -> None:
    st.subheader("Volumetric OOIP")
    st.caption("Calculates initial oil-in-place from bulk volume and PVT inputs.")
    v_bulk = st.number_input("Bulk volume, V (acre-ft)", value=1000.0, format="%.2f")
    phi = st.number_input("Porosity, phi", value=0.20, format="%.4f")
    swc = st.number_input("Connate water saturation, Swc", value=0.25, format="%.4f")
    boi = st.number_input("Initial oil FVF, Boi (rb/STB)", value=1.20, format="%.6f")
    if st.button("Calculate OOIP", key="tools_ooip_calc"):
        result = oil_mbe.calc_volumetric_ooip(v_bulk, phi, swc, boi)
        st.success(f"Initial oil-in-place: {_fmt(result)} STB")


def _render_gas_expansion_tab() -> None:
    st.subheader("Gas Expansion Factor")
    st.caption("Computes Bg and Eg from PVT inputs.")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Current condition**")
        z = st.number_input("Z", value=0.85, format="%.6f", key="tools_bg_z")
        t = st.number_input("T (R)", value=660.0, format="%.2f", key="tools_bg_t")
        p = st.number_input("P (psia)", value=3000.0, format="%.2f", key="tools_bg_p")
    with col2:
        st.markdown("**Initial condition**")
        zi = st.number_input("Zi", value=0.95, format="%.6f", key="tools_eg_zi")
        ti = st.number_input("Ti (R)", value=660.0, format="%.2f", key="tools_eg_ti")
        pi = st.number_input("Pi (psia)", value=3500.0, format="%.2f", key="tools_eg_pi")

    if st.button("Calculate Bg and Eg", key="tools_bg_calc"):
        bg = pvt.calc_bg_from_pvt(z, t, p)
        eg = pvt.calc_eg_from_pvt(zi, ti, pi)
        body = f"""
        <p style="margin: 5px 0;"><b>Bg:</b> {_fmt(bg)} rb/SCF</p>
        <p style="margin: 5px 0;"><b>Eg:</b> {_fmt(eg)} rb/SCF</p>
        """
        st.markdown(_style_box(body, accent="#1f2430"), unsafe_allow_html=True)


def _render_free_gas_balance_tab() -> None:
    st.subheader("Free Gas Balance")
    st.caption("Standalone saturation utility using the handout formula for Method 2.")

    col1, col2 = st.columns(2)
    with col1:
        n = st.number_input("N (STB)", value=31_135_600.0, format="%.2f")
        np = st.number_input("Np (STB)", value=5_000_000.0, format="%.2f")
        bo = st.number_input("Bo (rb/STB)", value=1.17, format="%.6f")
        boi = st.number_input("Boi (rb/STB)", value=1.20, format="%.6f")
    with col2:
        swc = st.number_input("Swc", value=0.25, format="%.4f")
        g = st.number_input("G (SCF)", value=45_454_545.45, format="%.2f")
        bg = st.number_input("Bg (rb/SCF)", value=0.0050, format="%.6f")
        bgi = st.number_input("Bgi (rb/SCF)", value=0.0045, format="%.6f")

    gas_col1, gas_col2 = st.columns(2)
    with gas_col1:
        we = st.number_input("We (rb)", value=0.0, format="%.2f")
        wp = st.number_input("Wp (STB)", value=0.0, format="%.2f")
    with gas_col2:
        bw = st.number_input("Bw (rb/STB)", value=1.0, format="%.6f")
        include_drive = st.checkbox("Show gas drive-index cross-check", value=True)

    if st.button("Calculate Free Gas Saturation", key="tools_sg_calc"):
        if n <= 0:
            st.error("N must be greater than zero.")
            return

        method_1 = 1 - (np / n)
        method_2 = 1 - (1 - (np / n)) * (bo / boi) * (1 - swc)
        method_2 = max(0.0, min(1.0, method_2))

        st.success(f"Method 1 Sg: {_fmt(method_1, 4)}")
        st.success(f"Method 2 Sg: {_fmt(method_2, 4)}")

        balance_df = pd.DataFrame(
            {
                "Component": ["Method 1", "Method 2"],
                "Sg": [method_1, method_2],
            }
        )
        fig = px.bar(balance_df, x="Component", y="Sg", title="Free Gas Saturation Methods", text_auto=True)
        fig.update_layout(template="plotly_dark", yaxis_range=[0, 1])
        st.plotly_chart(fig, width='stretch')

        if include_drive:
            eg = gas_mbe.calc_eg_gas(bg, bgi)
            f = gas_mbe.calc_f_gas(g, bg, wp, bw)
            drive = gas_mbe.calc_drive_indices_gas(g, eg, 0.0, we, wp, bw, f)
            body = f"""
            <p style="margin: 5px 0;"><b>GEI:</b> {_fmt(drive['gei'])}</p>
            <p style="margin: 5px 0;"><b>EDI:</b> {_fmt(drive['edi'])}</p>
            <p style="margin: 5px 0;"><b>WDI:</b> {_fmt(drive['wdi'])}</p>
            <p style="margin: 5px 0;"><b>SUM:</b> {_fmt(drive['total'])}</p>
            """
            st.markdown(_style_box(body, accent="#1f2430"), unsafe_allow_html=True)


def render_tools_section() -> None:
    st.header("Additional Tools")
    st.markdown("Compact utility calculators for the MBE workflow.")

    volumetric_tab, expansion_tab, free_gas_tab = st.tabs(
        ["Volumetric OOIP", "Gas Expansion Factor", "Free Gas Balance"]
    )

    with volumetric_tab:
        _render_volumetric_tab()

    with expansion_tab:
        _render_gas_expansion_tab()

    with free_gas_tab:
        _render_free_gas_balance_tab()
