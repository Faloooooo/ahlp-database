import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# Page Settings
st.set_page_config(page_title="AHLP Management System", layout="wide", page_icon="🏨")

# Links & GIDs
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
        else: st.error("Wrong Password")
    st.stop()

# --- Navigation ---
st.sidebar.title("🏨 AHLP Dashboard")
mode = st.sidebar.radio("Main Menu:", ["📊 Analysis & Reports", "✍️ Data Entry"])

if mode == "✍️ Data Entry":
    cat = st.selectbox("Category:", ["Diesel (Fuel)", "Gas", "Water", "Generators", "EDL (State Electricity)"])
    with st.form("entry_form", clear_on_submit=True):
        if cat == "Diesel (Fuel)":
            st.subheader("⛽ Tank Levels (cm)")
            c1, c2 = st.columns(2)
            m = c1.number_input("Emergency (Main)")
            r = c2.number_input("Receiving")
            d = c1.number_input("Daily")
            b = c2.number_input("Boiler")
            st.divider()
            st.subheader("💰 New Purchase")
            bl = st.number_input("Bought Liters")
            bp = st.number_input("Total Price (USD)")
            vals, s_name = [m, r, d, b, bl, bp], "Fuel_Data"

        elif cat == "Water":
            st.subheader("🏙️ City Water")
            cw = st.number_input("Meter Reading m³"); cb = st.number_input("Bill USD"); cf = st.number_input("Other Fees USD")
            st.divider(); st.subheader("🚚 Water Trucks")
            tr = st.number_input("Truck Meter m³"); tc = st.number_input("Truck Count"); ts = st.number_input("Size m³"); tp = st.number_input("Total Truck Cost USD")
            vals, s_name = [cw, tc, ts, tp, cb, cf, tr], "Water_Data"

        elif cat == "Gas":
            st.subheader("🔥 Central Tank & Cylinders")
            vals, s_name = [st.number_input("Tank %"), st.number_input("Bought Liters"), st.number_input("Cylinders Qty"), st.number_input("Cylinders Price")], "Gas_Data"

        elif cat == "Generators":
            v = []
            for i in range(1, 6):
                st.subheader(f"⚡ Generator {i}")
                c1, c2 = st.columns(2)
                v.extend([c1.number_input(f"kWh G{i}", key=f"k{i}"), c2.number_input(f"SMU G{i}", key=f"s{i}")])
            vals, s_name = v, "Generators_kwh"

        elif cat == "EDL (State Electricity)":
            st.subheader("🔌 EDL Meters & Fees")
            vals, s_name = [st.number_input("Night"), st.number_input("Peak"), st.number_input("Day"), st.number_input("Rehab"), st.number_input("Losses"), st.number_input("Subscription"), st.number_input("VAT"), st.number_input("Total Bill")], "Electricity_Accrual"

        if st.form_submit_button("Submit Data"):
            if send_to_google(s_name, vals): st.success("✅ Data Saved Successfully")
            else: st.error("❌ Submission Failed")

else: # --- Reports & Analysis ---
    st.title("📈 Energy Analysis Center")
    report_view = st.sidebar.selectbox("Select Report View:", ["Monthly Budget Summary", "Diesel Detailed", "Water & Electricity"])
    
    col1, col2 = st.columns(2)
    start_d = col1.date_input("Start Date", datetime.now().replace(day=1))
    end_d = col2.date_input("End Date", datetime.now())

    if report_view == "Monthly Budget Summary":
        st.subheader(f"📋 Monthly Utility Summary ({start_d.strftime('%B %Y')})")
        df_f = load_data('fuel'); df_w = load_data('water'); df_e = load_data('electricity'); df_g = load_data('gas')
        
        # Calculate Logic
        summary = {
            "Description": ["Diesel Volume (L)", "Diesel Cost (USD)", "EDL Cost (USD)", "Water Cost (USD)", "Gas Cost (USD)"],
            "Total for Period": [0.0, 0.0, 0.0, 0.0, 0.0]
        }
        
        if not df_f.empty:
            f_f = df_f[(df_f['Timestamp'].dt.date >= start_d) & (df_f['Timestamp'].dt.date <= end_d)]
            summary["Total for Period"][0] = f_f['Bought_Liters'].sum() if 'Bought_Liters' in f_f.columns else 0
            summary["Total for Period"][1] = f_f['Price_USD'].sum() if 'Price_USD' in f_f.columns else 0
        if not df_e.empty:
            e_f = df_e[(df_e['Timestamp'].dt.date >= start_d) & (df_e['Timestamp'].dt.date <= end_d)]
            summary["Total for Period"][2] = e_f['Total_Bill_USD'].sum() if 'Total_Bill_USD' in e_f.columns else 0
        
        st.table(pd.DataFrame(summary))

    elif report_view == "Diesel Detailed":
        st.subheader("⛽ Diesel Consumption & Stock")
        df_f = load_data('fuel')
        if not df_f.empty:
            for c in ['Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm', 'Bought_Liters']:
                if c not in df_f.columns: df_f[c] = 0
            
            f_f = df_f[(df_f['Timestamp'].dt.date >= start_d) & (df_f['Timestamp'].dt.date <= end_d)]
            if len(f_f) >= 1:
                last = f_f.iloc[-1]
                cur_l = (last['Main_Tank_cm']*CONV['main']) + (last['Receiving_Tank_cm']*CONV['rec']) + (last['Daily_Tank_cm']*CONV['daily']) + (last['Boiler_Tank_cm']*CONV['boil'])
                st.metric("Total Current Stock (Liters)", f"{cur_l:,.1f} L")
                st.dataframe(f_f)

    elif report_view == "Water & Electricity":
        st.subheader("💧 Utility Tracking")
        st.info("Charts and detailed consumption tables for Water and EDL will appear here.")
