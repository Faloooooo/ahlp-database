import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Page Settings
st.set_page_config(page_title="AHLP Management System", layout="wide", page_icon="🏨")

# Links & Data Functions (same as previous)
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

# --- Authentication ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 AHLP Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- Navigation ---
mode = st.sidebar.radio("Navigation:", ["📊 Reports & Analytics", "✍️ Data Entry"])

if mode == "✍️ Data Entry":
    # (Data entry code remains the same as previous)
    st.info("Switch to Reports to see the results.")
    # [Internal Note: Keep the entry logic from the previous stable version]

else: # --- Reports & Analytics (The Rest of the Plan) ---
    st.title("📈 Operational Intelligence Dashboard")
    report_view = st.sidebar.selectbox("Select Report View:", ["Monthly Budget Summary", "Diesel & Generators", "Water & Gas", "EDL Analysis"])
    
    col1, col2 = st.columns(2)
    start_d = col1.date_input("Start Date", datetime.now().replace(day=1))
    end_d = col2.date_input("End Date", datetime.now())

    # --- 1. Monthly Budget Summary ---
    if report_view == "Monthly Budget Summary":
        st.subheader(f"📋 Global Energy & Utility Budget ({start_d.strftime('%B %Y')})")
        df_f = load_data('fuel'); df_w = load_data('water'); df_e = load_data('electricity'); df_g = load_data('gas')
        
        summary = {
            "Description": ["Diesel Total Cost", "Electricity (EDL) Cost", "Water Total Cost", "Gas Total Cost"],
            "Amount (USD)": [0.0, 0.0, 0.0, 0.0]
        }
        
        if not df_f.empty:
            summary["Amount (USD)"][0] = df_f[(df_f['Timestamp'].dt.date >= start_d) & (df_f['Timestamp'].dt.date <= end_d)]['Price_USD'].sum()
        if not df_e.empty:
            summary["Amount (USD)"][1] = df_e[(df_e['Timestamp'].dt.date >= start_d) & (df_e['Timestamp'].dt.date <= end_d)]['Total_Bill_USD'].sum()
        if not df_w.empty:
            w_f = df_w[(df_w['Timestamp'].dt.date >= start_d) & (df_w['Timestamp'].dt.date <= end_d)]
            summary["Amount (USD)"][2] = w_f['Truck_Cost_USD'].sum() + w_f['City_Bill_Total_USD'].sum()
        
        st.table(pd.DataFrame(summary))
        
        # Financial Pie Chart
        fig_pie = px.pie(pd.DataFrame(summary), values='Amount (USD)', names='Description', title='Cost Distribution')
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- 2. Diesel & Generators (Daily/Detailed) ---
    elif report_view == "Diesel & Generators":
        st.subheader("⛽ Diesel Consumption Analysis")
        df_f = load_data('fuel')
        if not df_f.empty:
            f_f = df_f[(df_f['Timestamp'].dt.date >= start_d) & (df_f['Timestamp'].dt.date <= end_d)]
            
            # Stock Trend Chart
            f_f['Total_Inventory'] = (f_f['Main_Tank_cm']*CONV['main']) + (f_f['Daily_Tank_cm']*CONV['daily'])
            fig_fuel = px.line(f_f, x='Timestamp', y='Total_Inventory', title='Fuel Inventory Trend (Liters)')
            st.plotly_chart(fig_fuel, use_container_width=True)
            
            st.subheader("⚡ Generator Run-hours (SMU)")
            df_gen = load_data('generators')
            if not df_gen.empty:
                st.dataframe(df_gen.tail(10))

    # --- 3. Water & Gas ---
    elif report_view == "Water & Gas":
        st.subheader("💧 Water & Gas Usage")
        df_w = load_data('water')
        if not df_w.empty:
            w_f = df_w[(df_w['Timestamp'].dt.date >= start_d) & (df_w['Timestamp'].dt.date <= end_d)]
            fig_water = px.bar(w_f, x='Timestamp', y='City_Water_Reading', title='City Water Meter Trend')
            st.plotly_chart(fig_water, use_container_width=True)

