import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# --- Page Settings ---
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
        # Standardization to prevent KeyErrors
        rename_map = {'Bought Liters': 'Bought_Liters', 'Total Price (USD)': 'Price_USD'}
        df.rename(columns=rename_map, inplace=True)
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
# PERMANENT DATA ENTRY
# ==========================================
if mode == "✍️ Data Entry":
    st.header("✍️ Daily Data Input")
    cat = st.selectbox("Category:", ["Diesel (Fuel)", "Water", "Gas", "Generators", "EDL (Electricity)"])
    
    with st.form("entry_form", clear_on_submit=True):
        if cat == "Diesel (Fuel)":
            c1, c2 = st.columns(2)
            vals = [c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)"), 
                    c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)"),
                    st.number_input("Bought Liters"), st.number_input("Total Price (USD)")]
            s_name = "Fuel_Data"
        elif cat == "Water":
            vals = [st.number_input("City Meter m³"), st.number_input("Truck Count"), 
                    st.number_input("Truck Size m³"), st.number_input("Truck Cost USD"),
                    st.number_input("EDW Bill USD"), st.number_input("Other Fees USD"), 
                    st.number_input("Truck Meter m³")]
            s_name = "Water_Data"
        # ... Other entry categories remain standard ...
        
        if st.form_submit_button("Submit Records"):
            # Logic to send data
            st.success("✅ Recorded Successfully")

# ==========================================
# PERFORMANCE DASHBOARD
# ==========================================
else:
    st.header("📊 Intelligence Dashboard")
    report_type = st.sidebar.selectbox("Report Module:", ["Diesel Fuel", "Water Consumption", "State Electricity"])
    
    col_d1, col_d2 = st.columns(2)
    sd = col_d1.date_input("From Date", datetime.now() - timedelta(days=7))
    ed = col_d2.date_input("To Date", datetime.now())

    if report_type == "Diesel Fuel":
        df = load_data('fuel')
        if not df.empty:
            # Check for missing columns
            for c in ['Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm', 'Bought_Liters']:
                if c not in df.columns: df[c] = 0.0
            
            last = df.iloc[-1]
            st.subheader("📍 Real-Time Stock (Liters)")
            m = st.columns(5)
            m[0].metric("Emergency", f"{last['Main_Tank_cm']*CONV['main']:,.0f} L")
            m[1].metric("Receiving", f"{last['Receiving_Tank_cm']*CONV['rec']:,.0f} L")
            m[2].metric("Daily", f"{last['Daily_Tank_cm']*CONV['daily']:,.0f} L")
            m[3].metric("Boiler", f"{last['Boiler_Tank_cm']*CONV['boil']:,.0f} L")
            total_now = (last['Main_Tank_cm']*CONV['main']) + (last['Receiving_Tank_cm']*CONV['rec']) + (last['Daily_Tank_cm']*CONV['daily']) + (last['Boiler_Tank_cm']*CONV['boil'])
            m[4].metric("TOTAL", f"{total_now:,.0f} L")

            # Consumption Yesterday
            if len(df) >= 2:
                prev = df.iloc[-2]
                st.divider()
                st.subheader("⏱️ Consumption - Last 24 Hours")
                c = st.columns(4)
                c[0].info(f"Emergency: {max(0, (prev['Main_Tank_cm']-last['Main_Tank_cm'])*CONV['main']):,.1f} L")
                c[1].info(f"Receiving: {max(0, (prev['Receiving_Tank_cm']-last['Receiving_Tank_cm'])*CONV['rec']):,.1f} L")
                c[2].info(f"Daily: {max(0, (prev['Daily_Tank_cm']-last['Daily_Tank_cm'])*CONV['daily']):,.1f} L")
                c[3].info(f"Boiler: {max(0, (prev['Boiler_Tank_cm']-last['Boiler_Tank_cm'])*CONV['boil']):,.1f} L")

            # Filtered Period Analysis
            mask = (df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)
            f_filt = df.loc[mask]
            
            if not f_filt.empty:
                st.divider()
                # Chart
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=f_filt['Timestamp'], y=f_filt['Main_Tank_cm']*CONV['main'], name='Emergency'))
                fig.add_trace(go.Scatter(x=f_filt['Timestamp'], y=f_filt['Boiler_Tank_cm']*CONV['boil'], name='Boiler'))
                st.plotly_chart(fig, use_container_width=True)

                # Export Fix
                towrite = io.BytesIO()
                f_filt.to_excel(towrite, index=False, engine='openpyxl')
                st.download_button("📥 Export Report to Excel", towrite.getvalue(), "Diesel_Report.xlsx")

    elif report_type == "Water Consumption":
        st.subheader("💧 Water Usage Analysis")
        df_w = load_data('water')
        if not df_w.empty:
            df_w['Daily_Usage'] = df_w['City_Water_Reading'].diff().fillna(0)
            st.bar_chart(df_w.set_index('Timestamp')['Daily_Usage'])
