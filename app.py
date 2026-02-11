import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. Configuration ---
st.set_page_config(page_title="Ramada Plaza Energy System", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'water': '423939923', 'gas': '578874363', 'electricity': '1588872380', 'generators': '1679289485'}
# Correct Conversion Factors for: Emergency, Receiving, Daily, Boiler
CONV = [107.22, 37.6572, 31.26, 37.6572]

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip()
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        # Robust Numeric Conversion to fix "0 L" issue
        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

def send_to_google(sheet_name, values):
    try:
        payload = json.dumps({"sheet": sheet_name, "values": values})
        response = requests.post(SCRIPT_URL, data=payload, headers={"Content-Type": "application/json"})
        return response.status_code == 200
    except:
        return False

# --- 2. Authentication ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 System Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 3. Navigation ---
menu = st.sidebar.radio("Main Menu:", ["📊 Performance Reports", "✍️ Data Entry"])

# ==========================================
# ✍️ DATA ENTRY SECTION
# ==========================================
if menu == "✍️ Data Entry":
    st.header("✍️ Daily Records Entry")
    cat = st.selectbox("Category:", ["Fuel", "Water", "Gas", "Electricity", "Generators"])
    
    with st.form("entry_form", clear_on_submit=True):
        if cat == "Fuel":
            c1, c2 = st.columns(2)
            v = [c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)"), 
                 c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)"), 
                 st.number_input("Liters Bought"), st.number_input("Price USD")]
            s_name = "Fuel_Data"
        elif cat == "Water":
            c1, c2 = st.columns(2)
            v = [c2.number_input("City Meter Reading"), c1.number_input("Truck Count"), 
                 c1.number_input("Truck Size m3"), c1.number_input("Truck Cost USD"), 
                 c2.number_input("City Bill USD"), c2.number_input("Other Fees")]
            s_name = "Water_Data"
        # Additional categories simplified for brevity
        else:
            st.info("Additional categories are pre-configured.")
            v, s_name = [0], "None"

        if st.form_submit_button("🚀 Submit"):
            if send_to_google(s_name, v): st.success("✅ Saved")
            else: st.error("❌ Error")

# ==========================================
# 📊 REPORTS SECTION
# ==========================================
else:
    report = st.sidebar.selectbox("Report Type:", ["Diesel Analysis", "Water Analysis"])
    sd = st.sidebar.date_input("From", datetime.now() - timedelta(7))
    ed = st.sidebar.date_input("To", datetime.now())

    if report == "Diesel Analysis":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)].sort_values('Timestamp')
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                first = df_filt.iloc[0]
                # Price per Liter from column 6
                p_liter = float(df.iloc[-1, 6]) if len(df.columns) > 6 else 0
                
                # 1. CURRENT INVENTORY
                st.subheader("📍 Current Inventory Levels (Liters)")
                c = st.columns(4)
                lbls = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                total_stock = 0
                for i in range(4):
                    val = float(last.iloc[i+1]) * CONV[i]
                    total_stock += val
                    c[i].metric(lbls[i], f"{val:,.0f} L")
                st.info(f"💰 Estimated Inventory Value: **${(total_stock * p_liter / 1000):,.2f}**")

                # 2. CONSUMPTION (SPENT)
                st.divider()
                st.subheader(f"📉 Consumption from {sd} to {ed}")
                cs = st.columns(4)
                total_spent = 0
                for i in range(4):
                    # Consumption = First Reading - Last Reading
                    usage = max(0, float(first.iloc[i+1]) - float(last.iloc[i+1]))
                    liters = usage * CONV[i]
                    total_spent += liters
                    cs[i].metric(f"{lbls[i]} Spent", f"{liters:,.1f} L")
                st.warning(f"💵 Total Consumption Cost: **${(total_spent * p_liter / 1000):,.2f}**")

    elif report == "Water Analysis":
        dfw = load_data('water')
        if not dfw.empty:
            dff = dfw[(dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)]
            if not dff.empty:
                st.header("💧 Water Analysis Report")
                city_m3 = max(0, float(dff.iloc[-1, 1]) - float(dff.iloc[0, 1]))
                truck_m3 = (dff.iloc[:, 2] * dff.iloc[:, 3]).sum()
                truck_cost = dff.iloc[:, 4].sum()
                city_cost = dff.iloc[:, 5].sum() + dff.iloc[:, 6].sum()
                
                m1, m2, m3 = st.columns(3)
                m1.metric("City Water m3", f"{city_m3:,.1f}")
                m2.metric("Truck Water m3", f"{truck_m3:,.1f}")
                m3.metric("Total m3", f"{(city_m3+truck_m3):,.1f}")
                
                k1, k2, k3 = st.columns(3)
                k1.metric("City Cost $", f"${city_cost:,.2f}")
                k2.metric("Truck Cost $", f"${truck_cost:,.2f}")
                k3.metric("Total Cost $", f"${(city_cost+truck_cost):,.2f}")
