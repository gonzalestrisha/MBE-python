import streamlit as st

st.set_page_config(page_title="MBE Calculator Pro", page_icon="🛢️", layout="wide")

st.title("Petroleum Reservoir MBE System")
st.markdown("Analyze Reservoir Performance, Energy Terms, and Drive Mechanisms.")
st.divider()

st.sidebar.header("Reservoir Settings")
selection = st.sidebar.radio(
	"Select Reservoir Type:",
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
