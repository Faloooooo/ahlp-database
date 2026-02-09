import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import io

# --- 1. Page Configuration ---
st.set_page_config(page_title="Ramada Plaza Energy System", layout="wide", page_icon="🏨")

# --- 2. Connections & Credentials ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxITTacKEMsGtc4V0aJOlJPnmcXEZrnyfM95tVOUWzcL1U7T8DYMWfEyEvyIwjyhGmW/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

# GIDs representing each sheet
GIDS = {'fuel': '1077908569', 'gas': '578874363', 'water': '423939923', 'electricity': '1588872380', 'generators': '1679289485'}
# Conversion Factors (cm to Liters)
CONV = {'main': 107.22, 'rec': 37.6572, 'daily': 31.26, 'boil': 37.6572}

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip()
        # Fix column names to match code expectations regardless of Excel header
        mapping = {'Bought Liters': 'Bought_Liters', 'Bought_Ltr': 'Bought_Liters', 'Price USD': 'Price_USD'}
        df.rename(columns=mapping, inplace=True)
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except Exception as e:
        return pd.DataFrame()

def send_to_google(sheet_name, values):
    try:
        # Important: Ensure values are sent as a simple list for Google Script
        payload = {"sheet": sheet_name, "values": values}
        response = requests.post(SCRIPT_URL, data=json.dumps(payload))
        return response.status_code == 200
    except:
        return False

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

# --- 4. Navigation ---
mode = st.sidebar.radio("Main Menu:", ["📊 Performance Reports", "✍️ Daily Data Entry"])

# ==========================================
# SECTION: DATA ENTRY (FIXED ORDER)
# ==========================================
if mode == "✍️ Daily Data Entry":
    st.header("✍️ Operational Data Recording")
    # THE ORDER YOU REQUESTED: Water, Gas, Electricity, Diesel, Generators
    category = st.selectbox("Select Utility:", ["Water", "Gas (Propane)", "EDL (Electricity)", "Diesel (Fuel)", "Generators"])
    
    with st.form("entry_form_secured", clear_on_submit=True):
        if category == "Water":
            st.subheader("🏙️ City Water & 🚚 Trucks")
            c1, c2 = st.columns(2)
            cw = c1.number_input("City Meter m³", step=0.1)
            tc = c2.number_input("Trucks Count", step=1)
            ts = c1.number_input("Truck Size m³", value=20.0)
            tp = c2.number_input("Total Trucks Cost (USD)", step=0.01)
            vals, s_name = [cw, tc, ts, tp, 0, 0, 0], "Water_Data"

        elif category == "Gas (Propane)":
            c1, c2 = st.columns(2)
            vals, s_name = [c1.number_input("Main Tank %"), c2.number_input("Bought Liters"), 
                            c1.number_input("Cylinders Count"), c2.number_input("Cylinders Price (USD)")], "Gas_Data"

        elif category == "EDL (Electricity)":
            c1, c2 = st.columns(2)
            vals, s_name = [c1.number_input("Night Reading"), c2.number_input("Peak Reading"), 
                            c1.number_input("Day Reading"), c2.number_input("Total Bill (USD)")], "Electricity_Accrual"

        elif category == "Diesel (Fuel)":
            c1, c2 = st.columns(2)
            m = c1.number_input("Emergency Tank (cm)")
            r = c2.number_input("Receiving Tank (cm)")
            d = c1.number_input("Daily Tank (cm)")
            b = c2.number_input("Boiler Tank (cm)")
            st.divider()
            bl = st.number_input("Bought Liters (Today)")
            bp = st.number_input("Total Fuel Cost (USD)")
            vals, s_name = [m, r, d, b, bl, bp], "Fuel_Data"

        elif category == "Generators":
            v = []
            for i in range(1, 4): # Simplified to 3 main generators
                st.write(f"**Generator {i}**")
                col1, col2 = st.columns(2)
                v.extend([col1.number_input(f"kWh G{i}", key=f"k{i}"), col2.number_input(f"Hours G{i}", key=f"h{i}")])
            vals, s_name = v, "Generators_kwh"

        if st.form_submit_button("🚀 Submit to Database"):
            # The logic that fixes "Submission Failed"
            if send_to_google(s_name, vals):
                st.success(f"✅ {category} data successfully uploaded!")
            else:
                st.error("❌ Link Error: Please check if Google Script is published as 'Anyone'.")

# ==========================================
# SECTION: FUEL REPORTS (ENHANCED)
# ==========================================
else:
    st.header("📊 Fuel Intelligence Dashboard")
    df = load_data('fuel')
    
    if not df.empty:
        # Fixing KeyError by ensuring columns exist
        for col in ['Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm', 'Bought_Liters']:
            if col not in df.columns: df[col] = 0.0

        last = df.iloc[-1]
        st.subheader("📍 Inventory Status")
        m = st.columns(4)
        l_m = last['Main_Tank_cm']*CONV['main']
        l_r = last['Receiving_Tank_cm']*CONV['rec']
        l_d = last['Daily_Tank_cm']*CONV['daily']
        l_b = last['Boiler_Tank_cm']*CONV['boil']
        
        m[0].metric("Emergency", f"{l_m:,.0f} L")
        m[1].metric("Receiving", f"{l_r:,.0f} L")
        m[2].metric("Daily", f"{l_d:,.0f} L")
        m[3].metric("Boiler", f"{l_b:,.0f} L")
        
        st.info(f"⚡ **Total Stock:** {l_m+l_r+l_d+l_b:,.0f} Liters")

        # Consumption Last Update
        if len(df) >= 2:
            prev = df.iloc[-2]
            st.divider()
            st.subheader("⏱️ Consumption (Last Entry vs Previous)")
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"**Emergency Diff:** {max(0, (prev['Main_Tank_cm']-last['Main_Tank_cm'])*CONV['main']):.1f} L")
            c2.write(f"**Receiving Diff:** {max(0, (prev['Receiving_Tank_cm']-last['Receiving_Tank_cm'])*CONV['rec']):.1f} L")
            c3.write(f"**Daily Diff:** {max(0, (prev['Daily_Tank_cm']-last['Daily_Tank_cm'])*CONV['daily']):.1f} L")
            c4.write(f"**Boiler Diff:** {max(0, (prev['Boiler_Tank_cm']-last['Boiler_Tank_cm'])*CONV['boil']):.1f} L")

        # Multi-Line Chart
        st.divider()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Main_Tank_cm']*CONV['main'], name='Emergency', line=dict(color='red')))
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Receiving_Tank_cm']*CONV['rec'], name='Receiving', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Daily_Tank_cm']*CONV['daily'], name='Daily', line=dict(color='green')))
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Boiler_Tank_cm']*CONV['boil'], name='Boiler', line=dict(color='orange')))
        st.plotly_chart(fig, use_container_width=True)

        # Secured Export (CSV to avoid ModuleNotFoundError)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Data (CSV)", csv, "Fuel_Report.csv", "text/csv")
