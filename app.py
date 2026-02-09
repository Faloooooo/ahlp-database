import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import io

# --- 1. الإعدادات والروابط ---
st.set_page_config(page_title="Ramada Plaza Energy System", layout="wide", page_icon="🏨")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
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
        payload = json.dumps({"sheet": sheet_name, "values": values})
        response = requests.post(SCRIPT_URL, data=payload, headers={"Content-Type": "application/json"})
        return response.status_code == 200
    except: return False

# --- 2. الدخول والنافذة الجانبية ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

mode = st.sidebar.radio("Main Menu:", ["📊 Performance Reports", "✍️ Daily Data Entry"])

# ==========================================
# SECTION: DATA ENTRY (ثابت ومجرب)
# ==========================================
if mode == "✍️ Daily Data Entry":
    st.header("✍️ Operational Data Recording")
    category = st.selectbox("Select Utility:", ["Water", "Gas (Propane)", "EDL (Electricity)", "Diesel (Fuel)", "Generators"])
    
    with st.form("entry_form", clear_on_submit=True):
        if category == "Water":
            c1, c2 = st.columns(2)
            vals = [c1.number_input("City Meter m³"), c2.number_input("Trucks Count"), 
                    c1.number_input("Truck Size m³"), c2.number_input("Truck Cost USD"), 0, 0, 0]
            s_name = "Water_Data"
        elif category == "Diesel (Fuel)":
            c1, c2 = st.columns(2)
            vals = [c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)"), 
                    c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)"),
                    st.number_input("Bought Liters"), st.number_input("Total Cost (USD)")]
            s_name = "Fuel_Data"
        # ... بقية الأقسام بنفس الترتيب
        
        if st.form_submit_button("🚀 Submit to Google Sheet"):
            if send_to_google(s_name, vals): st.success("✅ Data Sent Successfully!")
            else: st.error("❌ Link Error")

# ==========================================
# SECTION: FUEL REPORTS (تم استعادة الحسابات)
# ==========================================
else:
    st.header("📊 Diesel Intelligence Dashboard")
    df = load_data('fuel')
    
    if not df.empty:
        # تأمين أسماء الأعمدة لمنع KeyError
        for col in ['Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm', 'Bought_Liters']:
            if col not in df.columns: df[col] = 0.0

        last = df.iloc[-1]
        
        # 1. عرض المخزون الحالي
        st.subheader("📍 Current Stock Levels")
        m = st.columns(4)
        curr_vals = {
            'main': last['Main_Tank_cm']*CONV['main'],
            'rec': last['Receiving_Tank_cm']*CONV['rec'],
            'daily': last['Daily_Tank_cm']*CONV['daily'],
            'boil': last['Boiler_Tank_cm']*CONV['boil']
        }
        m[0].metric("Emergency", f"{curr_vals['main']:,.0f} L")
        m[1].metric("Receiving", f"{curr_vals['rec']:,.0f} L")
        m[2].metric("Daily", f"{curr_vals['daily']:,.0f} L")
        m[3].metric("Boiler", f"{curr_vals['boil']:,.0f} L")
        st.info(f"⚡ **Total Stock:** {sum(curr_vals.values()):,.0f} Liters")

        # 2. حساب المصروف في آخر تحديث (ما تم طلبه)
        if len(df) >= 2:
            prev = df.iloc[-2]
            st.divider()
            st.subheader("📉 Consumption in Last Update (Liters)")
            c = st.columns(4)
            
            # المعادلة: (القراءة السابقة - القراءة الحالية) * معامل التحويل
            diff_m = max(0, (prev['Main_Tank_cm'] - last['Main_Tank_cm']) * CONV['main'])
            diff_r = max(0, (prev['Receiving_Tank_cm'] - last['Receiving_Tank_cm']) * CONV['rec'])
            diff_d = max(0, (prev['Daily_Tank_cm'] - last['Daily_Tank_cm']) * CONV['daily'])
            diff_b = max(0, (prev['Boiler_Tank_cm'] - last['Boiler_Tank_cm']) * CONV['boil'])
            
            c[0].write(f"**Emergency:** {diff_m:,.1f} L")
            c[1].write(f"**Receiving:** {diff_r:,.1f} L")
            c[2].write(f"**Daily:** {diff_d:,.1f} L")
            c[3].write(f"**Boiler:** {diff_b:,.1f} L")

        # 3. التحليل البياني الرباعي
        st.divider()
        st.subheader("📈 Trend Analysis (All Tanks)")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Main_Tank_cm']*CONV['main'], name='Emergency'))
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Receiving_Tank_cm']*CONV['rec'], name='Receiving'))
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Daily_Tank_cm']*CONV['daily'], name='Daily'))
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Boiler_Tank_cm']*CONV['boil'], name='Boiler'))
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # 4. التصدير
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Report (CSV)", csv, "diesel_report.csv", "text/csv")
