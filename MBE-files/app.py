import streamlit as st

#TODO: CHANGE ALL IMPORT PATHS

st.set_page_config(
	page_title="MBE Python",
	page_icon="🛢️",
	layout="wide",
)

st.title("MBE Python")
st.markdown("Reservoir material balance tools for oil, gas, and supporting utilities.")

selection = st.sidebar.radio(
	"Reservoir type",
	("Oil Reservoir", "Gas Reservoir", "Additional Tools"),
)

if selection == "Oil Reservoir":
	from ui.oil_ui import render_oil_section

	render_oil_section()
elif selection == "Gas Reservoir":
	from ui.gas_ui import render_gas_section

	render_gas_section()
elif selection == "Additional Tools":
	from ui.tools_ui import render_tools_section

	render_tools_section()
