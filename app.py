import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# --- Page Config ---
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
        # Auto-Correction for Common Column Names to prevent KeyError
        rename_map = {
            'Bought Liters': 'Bought_Liters', 'Bought_Ltr': 'Bought_Liters',
            'Price USD': 'Price_USD', 'Total Price (USD)': 'Price_USD', 'Total Price': 'Price_USD'
        }
        df.rename(columns=rename_map, inplace=True)
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except: return pd.DataFrame()

def send_to_google(sheet_name, values):
    try:
        response = requests.post(f"{SCRIPT_URL}?sheet={sheet_name}", data=json.dumps({"values": values}))
        return response.status_code == 200
    except: return False

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
# SECTION 1: PERMANENT DATA ENTRY
# ==========================================
if mode == "✍️ Data Entry":
    st.header("✍️ Record Daily Consumption")
    cat = st.selectbox("Select Category:", ["Diesel (Fuel)", "Water", "Gas (Propane)", "Generators", "EDL (Electricity)"])
    
    with st.form("main_entry_form", clear_on_submit=True):
        if cat == "Diesel (Fuel)":
            c1, c2 = st.columns(2)
            m = c1.number_input("Emergency Tank (cm)")
            r = c2.number_input("Receiving Tank (cm)")
            d = c1.number_input("Daily Tank (cm)")
            b = c2.number_input("Boiler Tank (cm)")
            st.divider()
            bl = st.number_input("Bought Liters")
            bp = st.number_input("Total Purchase Price (USD)")
            vals, s_name = [m, r, d, b, bl, bp], "Fuel_Data"

        elif cat == "Water":
            st.subheader("City Water & Trucks")
            vals = [st.number_input("City Meter m³"), st.number_input("Truck Count"), 
                    st.number_input("Truck Size m³"), st.number_input("Truck Cost USD"),
                    st.number_input("EDW Bill USD"), st.number_input("Other Fees USD"), 
                    st.number_input("Truck Meter m³")]
            s_name = "Water_Data"

        elif cat == "Gas (Propane)":
            vals = [st.number_input("Tank %"), st.number_input("Bought Ltr"), 
                    st.number_input("Cylinders Qty"), st.number_input("Cylinders Price")]
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

        if st.form_submit_button("Submit Data"):
            if send_to_google(s_name, vals): st.success("✅ Data Recorded")
            else: st.error("❌ Failed to send")

# ==========================================
# SECTION 2: INTELLIGENT FUEL REPORT
# ==========================================
else:
    st.header("📊 Fuel Intelligence & Inventory")
    df = load_data('fuel')
    
    # Pre-checks for required columns to avoid Red Screen Errors
    req = ['Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm', 'Bought_Liters']
    for col in req:
        if col not in df.columns: df[col] = 0.0

    col1, col2 = st.columns(2)
    sd = col1.date_input("From Date", datetime.now() - timedelta(days=7))
    ed = col2.date_input("To Date", datetime.now())

    if not df.empty:
        # 1. Current Stock (Liters)
        last = df.iloc[-1]
        l_main, l_rec = last['Main_Tank_cm']*CONV['main'], last['Receiving_Tank_cm']*CONV['rec']
        l_daily, l_boil = last['Daily_Tank_cm']*CONV['daily'], last['Boiler_Tank_cm']*CONV['boil']
        total_now = l_main + l_rec + l_daily + l_boil

        st.subheader("📍 Current Inventory Levels")
        m = st.columns(5)
        m[0].metric("Emergency", f"{l_main:,.0f} L")
        m[1].metric("Receiving", f"{l_rec:,.0f} L")
        m[2].metric("Daily", f"{l_daily:,.0f} L")
        m[3].metric("Boiler", f"{l_boil:,.0f} L")
        m[4].metric("TOTAL STOCK", f"{total_now:,.0f} L")

        # 2. Consumption Last Update (Yesterday)
        if len(df) >= 2:
            prev = df.iloc[-2]
            st.divider()
            st.subheader("⏱️ Consumption in Last Update")
            c = st.columns(4)
            c[0].info(f"Emergency: {max(0, (prev['Main_Tank_cm']-last['Main_Tank_cm'])*CONV['main']):,.1f} L")
            c[1].info(f"Receiving: {max(0, (prev['Receiving_Tank_cm']-last['Receiving_Tank_cm'])*CONV['rec']):,.1f} L")
            c[2].info(f"Daily: {max(0, (prev['Daily_Tank_cm']-last['Daily_Tank_cm'])*CONV['daily']):,.1f} L")
            c[3].info(f"Boiler: {max(0, (prev['Boiler_Tank_cm']-last['Boiler_Tank_cm'])*CONV['boil']):,.1f} L")

        # 3. Period Consumption Logic
        mask = (df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)
        f_filt = df.loc[mask]
        
        if not f_filt.empty:
            st.divider()
            start_vol = (f_filt.iloc[0]['Main_Tank_cm']*CONV['main']) + (f_filt.iloc[0]['Receiving_Tank_cm']*CONV['rec']) + (f_filt.iloc[0]['Daily_Tank_cm']*CONV['daily']) + (f_filt.iloc[0]['Boiler_Tank_cm']*CONV['boil'])
            period_cons = (start_vol + f_filt['Bought_Liters'].sum()) - total_now
            st.subheader(f"📅 Period Summary ({sd} to {ed})")
            st.warning(f"Total Fuel Consumed in this period: **{period_cons:,.1f} Liters**")

            # 4. Comprehensive Chart (4 Tanks)
            fig = go.Figure()
            tanks = {'Main_Tank_cm': 'Emergency', 'Receiving_Tank_cm': 'Receiving', 'Daily_Tank_cm': 'Daily', 'Boiler_Tank_cm': 'Boiler'}
            for col, name in tanks.items():
                conv_key = col.lower().split('_')[0][:4] if 'boiler' not in col else 'boil'
                fig.add_trace(go.Scatter(x=f_filt['Timestamp'], y=f_filt[col]*CONV.get(conv_key, 1), name=name))
            fig.update_layout(title="Multi-Tank Inventory Trend (Liters)", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            # 5. Export Button
            buffer = io.BytesIO()
            f_filt.to_excel(buffer, index=False)
            st.download_button("📥 Export Diesel Report to Excel", buffer.getvalue(), "Diesel_Report.xlsx", "application/vnd.ms-excel")
