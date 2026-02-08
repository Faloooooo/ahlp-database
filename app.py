import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# Page Settings
st.set_page_config(page_title="AHLP Management System", layout="wide", page_icon="🏨")

# Connections & Constants
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

def send_to_google(sheet_name, values):
    try:
        response = requests.post(f"{SCRIPT_URL}?sheet={sheet_name}", data=json.dumps({"values": values}))
        return response.status_code == 200
    except: return False

# --- Authentication ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 AHLP System Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == "AHLP2026":
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- Navigation ---
mode = st.sidebar.radio("Navigation:", ["📊 Performance Reports", "✍️ Data Entry"])

# ==========================================
# SECTION 1: DATA ENTRY (FIXED)
# ==========================================
if mode == "✍️ Data Entry":
    st.header("✍️ Daily Data Input")
    cat = st.selectbox("Category:", ["Diesel (Fuel)", "Water", "Gas (Propane)", "Generators", "EDL (Electricity)"])
    
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
            st.subheader("🏙️ City Water")
            cw = st.number_input("Meter Reading m³"); cb = st.number_input("Bill USD"); cf = st.number_input("Other Fees USD")
            st.divider(); st.subheader("🚚 Water Trucks")
            tr = st.number_input("Truck Meter m³"); tc = st.number_input("Truck Count"); ts = st.number_input("Size m³"); tp = st.number_input("Total Trucks Cost USD")
            vals, s_name = [cw, tc, ts, tp, cb, cf, tr], "Water_Data"

        elif cat == "Gas (Propane)":
            vals, s_name = [st.number_input("Tank %"), st.number_input("Bought Ltr"), st.number_input("Cylinders Qty"), st.number_input("Cylinders Price")], "Gas_Data"

        elif cat == "Generators":
            v = []
            for i in range(1, 6):
                st.subheader(f"Generator {i}")
                col1, col2 = st.columns(2)
                v.extend([col1.number_input(f"kWh G{i}"), col2.number_input(f"SMU G{i}")])
            vals, s_name = v, "Generators_kwh"

        elif cat == "EDL (Electricity)":
            vals, s_name = [st.number_input("Night"), st.number_input("Peak"), st.number_input("Day"), st.number_input("Rehab"), st.number_input("Losses"), st.number_input("Sub"), st.number_input("VAT"), st.number_input("Total")], "Electricity_Accrual"

        if st.form_submit_button("Submit Data"):
            if send_to_google(s_name, vals): st.success("✅ Data Recorded")
            else: st.error("❌ Failed to send")

# ==========================================
# SECTION 2: DIESEL REPORTS (ENHANCED)
# ==========================================
else:
    st.header("📊 Diesel Performance Dashboard")
    df_f = load_data('fuel')
    
    col_d1, col_d2 = st.columns(2)
    sd = col_d1.date_input("From Date", datetime.now() - timedelta(days=30))
    ed = col_d2.date_input("To Date", datetime.now())

    if not df_f.empty:
        # 1. CURRENT STOCK (LAST RECORD)
        last = df_f.iloc[-1]
        l_main, l_rec = last['Main_Tank_cm']*CONV['main'], last['Receiving_Tank_cm']*CONV['rec']
        l_daily, l_boil = last['Daily_Tank_cm']*CONV['daily'], last['Boiler_Tank_cm']*CONV['boil']
        total_now = l_main + l_rec + l_daily + l_boil

        st.subheader("📍 Current Inventory Levels")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Emergency", f"{l_main:,.0f} L")
        m2.metric("Receiving", f"{l_rec:,.0f} L")
        m3.metric("Daily", f"{l_daily:,.0f} L")
        m4.metric("Boiler", f"{l_boil:,.0f} L")
        m5.metric("TOTAL STOCK", f"{total_now:,.0f} L")

        # 2. CONSUMPTION (LAST UPDATE vs PREVIOUS)
        if len(df_f) >= 2:
            prev = df_f.iloc[-2]
            st.divider()
            st.subheader("⏱️ Consumption in Last Update (Yesterday/Last Entry)")
            c1, c2, c3, c4 = st.columns(4)
            def diff_l(cur, pre, f): 
                d = (pre - cur) * f
                return d if d > 0 else 0
            
            c1.write(f"**Emergency:** {diff_l(last['Main_Tank_cm'], prev['Main_Tank_cm'], CONV['main']):,.1f} L")
            c2.write(f"**Receiving:** {diff_l(last['Receiving_Tank_cm'], prev['Receiving_Tank_cm'], CONV['rec']):,.1f} L")
            c3.write(f"**Daily:** {diff_l(last['Daily_Tank_cm'], prev['Daily_Tank_cm'], CONV['daily']):,.1f} L")
            c4.write(f"**Boiler:** {diff_l(last['Boiler_Tank_cm'], prev['Boiler_Tank_cm'], CONV['boil']):,.1f} L")

        # 3. CONSUMPTION FOR SELECTED PERIOD
        mask = (df_f['Timestamp'].dt.date >= sd) & (df_f['Timestamp'].dt.date <= ed)
        f_filt = df_f.loc[mask]
        if len(f_filt) >= 2:
            st.divider()
            start_rec = f_filt.iloc[0]
            end_rec = f_filt.iloc[-1]
            old_total = (start_rec['Main_Tank_cm']*CONV['main']) + (start_rec['Receiving_Tank_cm']*CONV['rec']) + (start_rec['Daily_Tank_cm']*CONV['daily']) + (start_rec['Boiler_Tank_cm']*CONV['boil'])
            new_total = (end_rec['Main_Tank_cm']*CONV['main']) + (end_rec['Receiving_Tank_cm']*CONV['rec']) + (end_rec['Daily_Tank_cm']*CONV['daily']) + (end_rec['Boiler_Tank_cm']*CONV['boil'])
            period_cons = (old_total + f_filt['Bought_Liters'].sum()) - new_total
            st.subheader(f"📅 Total Consumption for Selected Period")
            st.info(f"Between {sd} and {ed}, the total consumption was: **{period_cons:,.1f} Liters**")

        # 4. CHART (ALL 4 TANKS)
        st.divider()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=f_filt['Timestamp'], y=f_filt['Main_Tank_cm']*CONV['main'], name='Emergency', line=dict(width=3)))
        fig.add_trace(go.Scatter(x=f_filt['Timestamp'], y=f_filt['Receiving_Tank_cm']*CONV['rec'], name='Receiving'))
        fig.add_trace(go.Scatter(x=f_filt['Timestamp'], y=f_filt['Daily_Tank_cm']*CONV['daily'], name='Daily'))
        fig.add_trace(go.Scatter(x=f_filt['Timestamp'], y=f_filt['Boiler_Tank_cm']*CONV['boil'], name='Boiler', line=dict(dash='dot')))
        fig.update_layout(title="Liters Analysis (All Tanks)", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # 5. EXPORT
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            f_filt.to_excel(writer, index=False, sheet_name='Fuel_Data')
        st.download_button("📥 Download Excel Report", buffer.getvalue(), f"Diesel_Report_{sd}_to_{ed}.xlsx", "application/vnd.ms-excel")
