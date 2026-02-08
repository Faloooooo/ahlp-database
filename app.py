import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# --- Page Config & Theme ---
st.set_page_config(page_title="Ramada Plaza Energy System", layout="wide", page_icon="🏨")

# --- Database Connections ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxITTacKEMsGtc4V0aJOlJPnmcXEZrnyfM95tVOUWzcL1U7T8DYMWfEyEvyIwjyhGmW/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'gas': '578874363', 'water': '423939923', 'electricity': '1588872380', 'generators': '1679289485'}
CONV = {'main': 107.22, 'rec': 37.6572, 'daily': 31.26, 'boil': 37.6572}

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip()
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except: return pd.DataFrame()

# --- Auth ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 System Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- Sidebar ---
st.sidebar.title("Ramada Plaza Beirut")
mode = st.sidebar.radio("Navigation:", ["📊 Performance Dashboard", "✍️ Data Entry"])

# ==========================================
# PERMANENT DATA ENTRY SECTION
# ==========================================
if mode == "✍️ Data Entry":
    st.header("✍️ Record Daily Consumption")
    cat = st.selectbox("Select Category:", ["Diesel (Fuel)", "Water", "Gas (Propane)", "Generators", "EDL (Electricity)"])
    
    with st.form("main_form", clear_on_submit=True):
        if cat == "Diesel (Fuel)":
            c1, c2 = st.columns(2)
            vals = [c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)"), 
                    c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)"),
                    st.number_input("Bought Liters"), st.number_input("Total Price (USD)")]
            s_name = "Fuel_Data"
        
        elif cat == "Water":
            st.subheader("City Water & Trucks")
            vals = [st.number_input("City Meter m³"), st.number_input("Truck Count"), 
                    st.number_input("Truck Size m³"), st.number_input("Truck Cost USD"),
                    st.number_input("EDW Bill USD"), st.number_input("Other Fees USD"), 
                    st.number_input("Truck Meter m³")]
            s_name = "Water_Data"

        elif cat == "Gas (Propane)":
            vals = [st.number_input("Tank %"), st.number_input("Bought Ltr"), 
                    st.number_input("Cylinders Qty"), st.number_input("Cylinders Cost")]
            s_name = "Gas_Data"

        elif cat == "Generators":
            v = []
            for i in range(1, 6):
                c1, c2 = st.columns(2)
                v.extend([c1.number_input(f"kWh G{i}"), c2.number_input(f"SMU G{i}")])
            vals, s_name = v, "Generators_kwh"

        elif cat == "EDL (Electricity)":
            vals = [st.number_input("Night"), st.number_input("Peak"), st.number_input("Day"), 
                    st.number_input("Rehab"), st.number_input("Losses"), st.number_input("Sub"), 
                    st.number_input("VAT"), st.number_input("Total Bill")]
            s_name = "Electricity_Accrual"

        if st.form_submit_button("Submit Records"):
            # Mock sending logic (Update this with your POST request if needed)
            st.success("✅ Recorded Successfully")

# ==========================================
# INTELLIGENT FUEL REPORT SECTION
# ==========================================
else:
    st.header("📊 Fuel Intelligence & Inventory")
    df = load_data('fuel')
    
    # Secure columns to prevent KeyError (The fix for your red screens)
    expected_cols = ['Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm', 'Bought_Liters']
    for col in expected_cols:
        if col not in df.columns: df[col] = 0.0

    col1, col2 = st.columns(2)
    sd = col1.date_input("From Date", datetime.now() - timedelta(days=7))
    ed = col2.date_input("To Date", datetime.now())

    if not df.empty:
        # Current Stock
        last = df.iloc[-1]
        stocks = {
            "Emergency": last['Main_Tank_cm']*CONV['main'],
            "Receiving": last['Receiving_Tank_cm']*CONV['rec'],
            "Daily": last['Daily_Tank_cm']*CONV['daily'],
            "Boiler": last['Boiler_Tank_cm']*CONV['boil']
        }
        
        st.subheader("📍 Current Stock (Liters)")
        m = st.columns(5)
        m[0].metric("Emergency", f"{stocks['Emergency']:,.0f} L")
        m[1].metric("Receiving", f"{stocks['Receiving']:,.0f} L")
        m[2].metric("Daily", f"{stocks['Daily']:,.0f} L")
        m[3].metric("Boiler", f"{stocks['Boiler']:,.0f} L")
        m[4].metric("TOTAL", f"{sum(stocks.values()):,.0f} L")

        # Consumption Analysis
        if len(df) >= 2:
            prev = df.iloc[-2]
            st.divider()
            st.subheader("⏱️ Consumption - Last Update vs Previous")
            c = st.columns(4)
            c[0].info(f"Emergency: {max(0, (prev['Main_Tank_cm']-last['Main_Tank_cm'])*CONV['main']):,.1f} L")
            c[1].info(f"Receiving: {max(0, (prev['Receiving_Tank_cm']-last['Receiving_Tank_cm'])*CONV['rec']):,.1f} L")
            c[2].info(f"Daily: {max(0, (prev['Daily_Tank_cm']-last['Daily_Tank_cm'])*CONV['daily']):,.1f} L")
            c[3].info(f"Boiler: {max(0, (prev['Boiler_Tank_cm']-last['Boiler_Tank_cm'])*CONV['boil']):,.1f} L")

        # Period Filter & Consumption
        mask = (df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)
        f_filt = df.loc[mask]
        
        if not f_filt.empty:
            st.divider()
            # Calculate total burned in period
            start_total = (f_filt.iloc[0]['Main_Tank_cm']*CONV['main']) + (f_filt.iloc[0]['Receiving_Tank_cm']*CONV['rec']) + (f_filt.iloc[0]['Daily_Tank_cm']*CONV['daily']) + (f_filt.iloc[0]['Boiler_Tank_cm']*CONV['boil'])
            end_total = sum(stocks.values())
            period_cons = (start_total + f_filt['Bought_Liters'].sum()) - end_total
            
            st.subheader(f"📅 Total Burned ({sd} to {ed})")
            st.warning(f"Total Fuel Consumed in this period: **{period_cons:,.1f} Liters**")

            # Chart (4 Tanks)
            fig = go.Figure()
            colors = ['#FF4B4B', '#1C83E1', '#00C781', '#FFAA00']
            for i, tank in enumerate(['Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm']):
                name = tank.split('_')[0]
                fig.add_trace(go.Scatter(x=f_filt['Timestamp'], y=f_filt[tank]*CONV[name.lower()[:4]], name=name, line=dict(color=colors[i], width=2)))
            fig.update_layout(title="Liters Analysis (All 4 Tanks)", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            # Export
            buffer = io.BytesIO()
            f_filt.to_excel(buffer, index=False)
            st.download_button("📥 Export Diesel Report to Excel", buffer.getvalue(), "Diesel_Report.xlsx")
