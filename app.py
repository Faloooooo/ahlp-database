import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# --- 1. Page Config ---
st.set_page_config(page_title="AHLP Management System", layout="wide", page_icon="🏨")

# --- 2. Connections ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxITTacKEMsGtc4V0aJOlJPnmcXEZrnyfM95tVOUWzcL1U7T8DYMWfEyEvyIwjyhGmW/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'gas': '578874363', 'water': '423939923', 'electricity': '1588872380', 'generators': '1679289485'}
CONV = {'main': 107.22, 'rec': 37.6572, 'daily': 31.26, 'boil': 37.6572}

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip()
        # Auto-fix column names
        rename_map = {'Bought Liters': 'Bought_Liters', 'Total Price (USD)': 'Price_USD'}
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

# --- 3. Authentication ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 AHLP System Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == "AHLP2026":
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 4. Sidebar Navigation ---
st.sidebar.title("🏨 Hotel Operations")
mode = st.sidebar.radio("Select Menu:", ["📊 Reports & Analytics", "✍️ Data Entry"])

# ==========================================
# SECTION: DATA ENTRY (FIXED & PERMANENT)
# ==========================================
if mode == "✍️ Data Entry":
    st.header("✍️ Daily Data Recording")
    category = st.selectbox("Category:", ["Diesel (Fuel)", "Water", "Gas (Propane)", "Generators", "EDL (Electricity)"])
    
    with st.form("entry_form_permanent", clear_on_submit=True):
        if category == "Diesel (Fuel)":
            c1, c2 = st.columns(2)
            m = c1.number_input("Emergency Tank (cm)")
            r = c2.number_input("Receiving Tank (cm)")
            d = c1.number_input("Daily Tank (cm)")
            b = c2.number_input("Boiler Tank (cm)")
            st.divider()
            bl = st.number_input("Bought Liters")
            bp = st.number_input("Total Purchase Price (USD)")
            vals, s_name = [m, r, d, b, bl, bp], "Fuel_Data"

        elif category == "Water":
            st.subheader("🏙️ City Water & 🚚 Trucks")
            c1, c2 = st.columns(2)
            cw = c1.number_input("City Meter m³"); cb = c2.number_input("EDW Bill USD")
            cf = c1.number_input("Other Fees USD"); tr = c2.number_input("Truck Meter m³")
            tc = c1.number_input("Truck Count"); ts = c2.number_input("Truck Size m³")
            tp = st.number_input("Total Trucks Cost USD")
            vals, s_name = [cw, tc, ts, tp, cb, cf, tr], "Water_Data"

        elif category == "Gas (Propane)":
            c1, c2 = st.columns(2)
            vals, s_name = [c1.number_input("Tank %"), c2.number_input("Bought Ltr"), 
                            c1.number_input("Cylinders Qty"), c2.number_input("Cylinders Price USD")], "Gas_Data"

        elif category == "Generators":
            v = []
            for i in range(1, 6):
                st.subheader(f"Generator {i}")
                col1, col2 = st.columns(2)
                v.extend([col1.number_input(f"kWh G{i}", key=f"kwh{i}"), col2.number_input(f"SMU G{i}", key=f"smu{i}")])
            vals, s_name = v, "Generators_kwh"

        elif category == "EDL (Electricity)":
            c1, c2 = st.columns(2)
            vals, s_name = [c1.number_input("Night"), c2.number_input("Peak"), c1.number_input("Day"), 
                            c2.number_input("Rehabilitation"), c1.number_input("Losses"), 
                            c2.number_input("Subscription"), c1.number_input("VAT"), 
                            c2.number_input("Total Bill USD")], "Electricity_Accrual"

        if st.form_submit_button("Submit Data"):
            if send_to_google(s_name, vals): st.success("✅ Recorded Successfully")
            else: st.error("❌ Submission Failed")

# ==========================================
# SECTION: REPORTS (FIXED & ENHANCED)
# ==========================================
else:
    st.header("📊 Intelligence Dashboard")
    report_view = st.sidebar.selectbox("Report View:", ["Diesel (Fuel)", "Water & Gas", "EDL Analysis"])
    
    col_d1, col_d2 = st.columns(2)
    sd = col_d1.date_input("Start Date", datetime.now() - timedelta(days=7))
    ed = col_d2.date_input("End Date", datetime.now())

    if report_view == "Diesel (Fuel)":
        df = load_data('fuel')
        if not df.empty:
            # Secure columns
            for c in ['Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm', 'Bought_Liters']:
                if c not in df.columns: df[c] = 0.0

            # 1. Current Stock (Metrics)
            last = df.iloc[-1]
            st.subheader("📍 Current Fuel Inventory")
            m = st.columns(5)
            l_m, l_r, l_d, l_b = last['Main_Tank_cm']*CONV['main'], last['Receiving_Tank_cm']*CONV['rec'], last['Daily_Tank_cm']*CONV['daily'], last['Boiler_Tank_cm']*CONV['boil']
            m[0].metric("Emergency", f"{l_m:,.0f} L")
            m[1].metric("Receiving", f"{l_r:,.0f} L")
            m[2].metric("Daily", f"{l_d:,.0f} L")
            m[3].metric("Boiler", f"{l_b:,.0f} L")
            m[4].metric("TOTAL STOCK", f"{l_m+l_r+l_d+l_b:,.0f} L")

            # 2. Consumption Last Entry (Yesterday)
            if len(df) >= 2:
                prev = df.iloc[-2]
                st.divider()
                st.subheader("⏱️ Consumption in Last Record")
                c = st.columns(4)
                c[0].info(f"Emergency: {max(0, (prev['Main_Tank_cm']-last['Main_Tank_cm'])*CONV['main']):,.1f} L")
                c[1].info(f"Receiving: {max(0, (prev['Receiving_Tank_cm']-last['Receiving_Tank_cm'])*CONV['rec']):,.1f} L")
                c[2].info(f"Daily: {max(0, (prev['Daily_Tank_cm']-last['Daily_Tank_cm'])*CONV['daily']):,.1f} L")
                c[3].info(f"Boiler: {max(0, (prev['Boiler_Tank_cm']-last['Boiler_Tank_cm'])*CONV['boil']):,.1f} L")

            # 3. Period Analysis & Chart
            mask = (df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)
            f_filt = df.loc[mask]
            if not f_filt.empty:
                st.divider()
                # Calculation for period
                start_vol = (f_filt.iloc[0]['Main_Tank_cm']*CONV['main']) + (f_filt.iloc[0]['Receiving_Tank_cm']*CONV['rec']) + (f_filt.iloc[0]['Daily_Tank_cm']*CONV['daily']) + (f_filt.iloc[0]['Boiler_Tank_cm']*CONV['boil'])
                period_cons = (start_vol + f_filt['Bought_Liters'].sum()) - (l_m+l_r+l_d+l_b)
                st.warning(f"📅 Total Fuel Consumed between {sd} and {ed}: **{period_cons:,.1f} Liters**")

                # Graph (All 4 Tanks)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=f_filt['Timestamp'], y=f_filt['Main_Tank_cm']*CONV['main'], name='Emergency'))
                fig.add_trace(go.Scatter(x=f_filt['Timestamp'], y=f_filt['Receiving_Tank_cm']*CONV['rec'], name='Receiving'))
                fig.add_trace(go.Scatter(x=f_filt['Timestamp'], y=f_filt['Daily_Tank_cm']*CONV['daily'], name='Daily'))
                fig.add_trace(go.Scatter(x=f_filt['Timestamp'], y=f_filt['Boiler_Tank_cm']*CONV['boil'], name='Boiler'))
                fig.update_layout(title="Liters Analysis (All Tanks)", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

                # Export
                towrite = io.BytesIO()
                f_filt.to_csv(towrite, index=False)
                st.download_button("📥 Export Period Data (CSV)", towrite.getvalue(), "Diesel_Report.csv", "text/csv")
