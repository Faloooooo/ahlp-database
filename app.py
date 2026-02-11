import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. Settings & Connections ---
st.set_page_config(page_title="Ramada Plaza Energy Management", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'water': '423939923', 'gas': '578874363', 'electricity': '1588872380', 'generators': '1679289485'}
CONV = [107.22, 37.6572, 31.26, 37.6572] # Conversion for: Emergency, Receiving, Daily, Boiler

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip()
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        # Force numeric conversion to avoid zeros
        for col in df.columns[1:6]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

def send_to_google(sheet_name, values):
    try:
        payload = json.dumps({"sheet": sheet_name, "values": values})
        response = requests.post(SCRIPT_URL, data=payload, headers={"Content-Type": "application/json"})
        return response.status_code == 200
    except: return False

# --- 2. Authentication ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 System Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"): st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 3. Sidebar Menu ---
menu = st.sidebar.radio("Navigation:", ["📊 Performance Reports", "✍️ Data Entry"])

# ==========================================
# ✍️ DATA ENTRY SECTION (English)
# ==========================================
if menu == "✍️ Data Entry":
    st.header("✍️ Daily Records Entry")
    cat = st.selectbox("Category:", ["Fuel (Diesel)", "Water", "Gas", "Electricity (EDL)", "Generators (5 Units)"])
    
    with st.form("entry_form"):
        if cat == "Fuel (Diesel)":
            c1, c2 = st.columns(2)
            v = [c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)"), c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)"), st.number_input("Liters Bought"), st.number_input("Price USD")]
            s_name = "Fuel_Data"
        elif cat == "Water":
            c1, c2 = st.columns(2)
            v = [c2.number_input("City Meter Reading"), c1.number_input("Truck Count"), c1.number_input("Truck Size M3", value=20.0), c1.number_input("Truck Cost USD"), c2.number_input("City Bill USD"), c2.number_input("Other Fees")]
            s_name = "Water_Data"
        elif cat == "Gas":
            v = [st.number_input("Tank Percentage %"), st.number_input("Cylinders Count"), st.number_input("Bought Liters"), st.number_input("Total Price USD")]
            s_name = "Gas_Data"
        elif cat == "Electricity (EDL)":
            v = [st.number_input("Night Reading"), st.number_input("Peak Reading"), st.number_input("Day Reading"), st.number_input("Total Bill USD")]
            s_name = "Electricity_Accrual"
        elif cat == "Generators (5 Units)":
            v = []
            for i in range(1, 6):
                c1, c2 = st.columns(2)
                v.extend([c1.number_input(f"Gen {i} kWh"), c2.number_input(f"Gen {i} SMU")])
            s_name = "Generators_kwh"
        
        if st.form_submit_button("🚀 Save Data"):
            if send_to_google(s_name, v): st.success("✅ Successfully Saved")
            else: st.error("❌ Transmission Error")

# ==========================================
# 📊 REPORTS SECTION (English)
# ==========================================
else:
    report = st.sidebar.selectbox("Report Type:", ["Diesel Analysis", "Water Analysis"])
    sd = st.sidebar.date_input("From Date", datetime.now()-timedelta(1))
    ed = st.sidebar.date_input("To Date", datetime.now())

    if report == "Diesel Analysis":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)].sort_values('Timestamp')
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                first = df_filt.iloc[0]
                # Price per Liter (Column 6)
                p_liter = float(df.iloc[-1, 6]) if len(df.columns) > 6 and df.iloc[-1, 6] != 0 else 0
                
                # A. Current Inventory
                st.subheader("📍 Current Inventory Levels (Liters)")
                c = st.columns(4)
                lbls = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                total_stock = 0
                for i in range(4):
                    val = float(last.iloc[i+1]) * CONV[i]
                    total_stock += val
                    c[i].metric(lbls[i], f"{val:,.0f} L")
                st.info(f"💰 Estimated Inventory Value: **${(total_stock * p_liter / 1000):,.2f}**")

                # B. Consumption (Spent)
                st.divider()
                st.subheader(f"📉 Consumption from {sd} to {ed}")
                cs = st.columns(4)
                total_spent = 0
                for i in range(4):
                    usage = max(0, float(first.iloc[i+1]) - float(last.iloc[i+1]))
                    lit_spent = usage * CONV[i]
                    total_spent += lit_spent
                    cs[i].metric(f"{lbls[i]} Spent", f"{lit_spent:,.1f} L")
                st.warning(f"💵 Total Consumption Cost: **${(total_spent * p_liter / 1000):,.2f}**")

    elif report == "Water Analysis":
        dfw = load_data('water')
        if not dfw.empty:
            dff = dfw[(dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)]
            if not dff.empty:
                st.header("💧 Water Analysis Report")
                city_m3 = max(0, float(dff.iloc[-1, 1]) - float(dff.iloc[0, 1]))
                truck_m3 = (dff.iloc[:, 2].astype(float) * dff.iloc[:, 3].astype(float)).sum()
                truck_c = dff.iloc[:, 4].astype(float).sum()
                city_c = dff.iloc[:, 5].astype(float).sum() + dff.iloc[:, 6].astype(float).sum()
                
                r1 = st.columns(3)
                r1[0].metric("City Water m³", f"{city_m3:,.1f}")
                r1[1].metric("Truck Water m³", f"{truck_m3:,.1f}")
                r1[2].metric("Total m³", f"{(city_m3+truck_m3):,.1f}")
                
                r2 = st.columns(3)
                r2[0].metric("City Cost $", f"${city_c:,.2f}")
                r2[1].metric("Truck Cost $", f"${truck_c:,.2f}")
                r2[2].metric("Total Cost $", f"${(city_c+truck_c):,.2f}")
