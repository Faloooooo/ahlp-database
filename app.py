import streamlit as st
import pandas as pd
import requests
import json
import plotly.express as px
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="AHLP Management System", layout="wide", page_icon="🏨")

# Connections
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
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- Sidebar Navigation ---
st.sidebar.title("Hotel Operations")
mode = st.sidebar.radio("Select Module:", ["📊 Operational Reports", "✍️ Data Entry"])

if mode == "✍️ Data Entry":
    st.header("✍️ Daily Data Input")
    category = st.selectbox("Category:", ["Diesel (Fuel)", "Gas (Propane)", "Water", "Generators", "EDL (State Electricity)"])
    
    with st.form("entry_form", clear_on_submit=True):
        if category == "Diesel (Fuel)":
            st.subheader("⛽ Tank Inventory (cm)")
            col_a, col_b = st.columns(2)
            m = col_a.number_input("Emergency (Main)")
            r = col_b.number_input("Receiving Tank")
            d = col_a.number_input("Daily Tank")
            b = col_b.number_input("Boiler Tank")
            st.divider()
            st.subheader("💰 Purchases")
            bought = st.number_input("Bought Liters", min_value=0.0)
            price = st.number_input("Total Purchase Cost (USD)", min_value=0.0)
            vals, s_name = [m, r, d, b, bought, price], "Fuel_Data"

        elif category == "Water":
            st.subheader("🏙️ City Water (EDW)")
            cw = st.number_input("Meter Reading m³"); cb = st.number_input("Monthly Bill USD"); cf = st.number_input("Other Fees USD")
            st.divider()
            st.subheader("🚚 Water Trucks (Extra)")
            tr = st.number_input("Truck Meter m³"); tc = st.number_input("Truck Count", step=1); ts = st.number_input("Truck Size m³"); tp = st.number_input("Total Trucks Cost USD")
            vals, s_name = [cw, tc, ts, tp, cb, cf, tr], "Water_Data"

        elif category == "Gas (Propane)":
            st.subheader("🔥 Gas Tanks & Cylinders")
            vals, s_name = [st.number_input("Main Tank %"), st.number_input("Bought Liters"), st.number_input("Cylinders Count"), st.number_input("Cylinders Cost USD")], "Gas_Data"

        elif category == "Generators":
            st.subheader("⚡ Generators Tracking")
            v = []
            for i in range(1, 6):
                c1, c2 = st.columns(2)
                v.extend([c1.number_input(f"kWh Gen {i}"), c2.number_input(f"SMU (Hours) Gen {i}")])
            vals, s_name = v, "Generators_kwh"

        elif category == "EDL (State Electricity)":
            st.subheader("🔌 EDL Meter Readings & Bill")
            vals, s_name = [st.number_input("Night"), st.number_input("Peak"), st.number_input("Day"), st.number_input("Rehabilitation"), st.number_input("Losses"), st.number_input("Subscription"), st.number_input("VAT"), st.number_input("Grand Total USD")], "Electricity_Accrual"

        if st.form_submit_button("Submit Data"):
            if send_to_google(s_name, vals): st.success(f"✅ {category} data recorded successfully!")
            else: st.error("❌ Error: Check connection.")

else: # --- Reports & Analytics (Fixed Version) ---
    st.header("📊 Performance & Analytics Dashboard")
    report_type = st.sidebar.selectbox("Report Type:", ["Monthly Summary Table", "Fuel & Energy Trends", "Water & Gas Detailed"])
    
    col_d1, col_d2 = st.columns(2)
    start_d = col_d1.date_input("From Date", datetime.now().replace(day=1))
    end_d = col_d2.date_input("To Date", datetime.now())

    # --- Fixed Logic to prevent KeyError ---
    df_f = load_data('fuel')
    if not df_f.empty:
        # Check and create missing columns to avoid error from photo
        for col in ['Price_USD', 'Bought_Liters', 'Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm']:
            if col not in df_f.columns: df_f[col] = 0.0

        mask = (df_f['Timestamp'].dt.date >= start_d) & (df_f['Timestamp'].dt.date <= end_d)
        f_filtered = df_f.loc[mask]

        if report_type == "Monthly Summary Table":
            st.subheader(f"📋 Utility Summary - {start_d.strftime('%B %Y')}")
            # Dynamic Summary mimicking your Excel Photo
            summary_tbl = {
                "Item Description": ["Diesel Cost (USD)", "Diesel Volume (L)", "State Electricity (EDL) Cost", "Water Cost (USD)", "Gas Cost (USD)"],
                "Total for Selection": [f_filtered['Price_USD'].sum(), f_filtered['Bought_Liters'].sum(), 0.0, 0.0, 0.0]
            }
            st.table(pd.DataFrame(summary_tbl))
            
            # Pie Chart
            fig_pie = px.pie(names=summary_tbl["Item Description"], values=[v if v > 0 else 1 for v in summary_tbl["Total for Selection"]], title="Cost Distribution (Preview)")
            st.plotly_chart(fig_pie)

        elif report_type == "Fuel & Energy Trends":
            st.subheader("⛽ Diesel Consumption Analysis")
            if not f_filtered.empty:
                f_filtered['Total_L'] = (f_filtered['Main_Tank_cm']*CONV['main']) + (f_filtered['Daily_Tank_cm']*CONV['daily'])
                st.line_chart(f_filtered.set_index('Timestamp')['Total_L'])
                st.dataframe(f_filtered)
