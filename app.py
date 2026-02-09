import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import io

# --- الإعدادات الأساسية ---
st.set_page_config(page_title="Ramada Plaza Energy System", layout="wide", page_icon="🏨")

# الرابط الجديد الذي زودتني به
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
        # إرسال الطلب بصيغة JSON متوافقة مع الرابط الجديد
        payload = json.dumps({"sheet": sheet_name, "values": values})
        # إضافة "follow redirects" لأن روابط جوجل تتطلب ذلك
        response = requests.post(SCRIPT_URL, data=payload, headers={"Content-Type": "application/json"})
        # إذا كانت النتيجة تحتوي على كلمة "Success" أو كود 200
        if response.status_code == 200:
            return True
        return False
    except:
        return False

# --- تسجيل الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- القائمة الجانبية ---
mode = st.sidebar.radio("Main Menu:", ["📊 Performance Reports", "✍️ Daily Data Entry"])

if mode == "✍️ Daily Data Entry":
    st.header("✍️ Operational Data Recording")
    # الترتيب الثابت: المياه، الغاز، الكهرباء، المازوت، المولدات
    category = st.selectbox("Select Utility:", ["Water", "Gas (Propane)", "EDL (Electricity)", "Diesel (Fuel)", "Generators"])
    
    with st.form("fixed_entry_form", clear_on_submit=True):
        if category == "Water":
            c1, c2 = st.columns(2)
            cw = c1.number_input("City Meter m³", step=0.1)
            tc = c2.number_input("Trucks Count", step=1)
            ts = c1.number_input("Truck Size m³", value=20.0)
            tp = c2.number_input("Total Trucks Cost (USD)", step=0.01)
            # إرسال 7 قيم لتناسب أعمدة الشيت
            vals, s_name = [cw, tc, ts, tp, 0, 0, 0], "Water_Data"

        elif category == "Gas (Propane)":
            c1, c2 = st.columns(2)
            vals, s_name = [c1.number_input("Main Tank %"), c2.number_input("Bought Liters"), 
                            c1.number_input("Cylinders Count"), c2.number_input("Cylinders Price (USD)")], "Gas_Data"

        elif category == "EDL (Electricity)":
            c1, c2 = st.columns(2)
            vals, s_name = [c1.number_input("Night"), c2.number_input("Peak"), 
                            c1.number_input("Day"), c2.number_input("Total Bill (USD)")], "Electricity_Accrual"

        elif category == "Diesel (Fuel)":
            c1, c2 = st.columns(2)
            vals, s_name = [c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)"), 
                            c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)"),
                            st.number_input("Bought Liters"), st.number_input("Total Cost (USD)")], "Fuel_Data"

        elif category == "Generators":
            v = []
            for i in range(1, 4): # 3 مولدات
                st.write(f"Generator {i}")
                col1, col2 = st.columns(2)
                v.extend([col1.number_input(f"kWh G{i}", key=f"kg{i}"), col2.number_input(f"Hours G{i}", key=f"hg{i}")])
            vals, s_name = v, "Generators_kwh"

        if st.form_submit_button("🚀 Submit to Google Sheet"):
            if send_to_google(s_name, vals):
                st.success("✅ Data successfully sent to Excel!")
            else:
                st.error("❌ Submission Failed. Check App Script Deployment.")

else: # قسم تقرير المازوت المطور
    st.header("📊 Fuel Intelligence Dashboard")
    df = load_data('fuel')
    if not df.empty:
        # تأمين الأعمدة
        for col in ['Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm', 'Bought_Liters']:
            if col not in df.columns: df[col] = 0.0

        last = df.iloc[-1]
        st.subheader("📍 Current Inventory Status")
        m = st.columns(4)
        m[0].metric("Emergency", f"{last['Main_Tank_cm']*CONV['main']:,.0f} L")
        m[1].metric("Receiving", f"{last['Receiving_Tank_cm']*CONV['rec']:,.0f} L")
        m[2].metric("Daily", f"{last['Daily_Tank_cm']*CONV['daily']:,.0f} L")
        m[3].metric("Boiler", f"{last['Boiler_Tank_cm']*CONV['boil']:,.0f} L")
        
        # الرسم البياني الرباعي
        st.divider()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Main_Tank_cm']*CONV['main'], name='Emergency'))
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Receiving_Tank_cm']*CONV['rec'], name='Receiving'))
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Daily_Tank_cm']*CONV['daily'], name='Daily'))
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Boiler_Tank_cm']*CONV['boil'], name='Boiler'))
        st.plotly_chart(fig, use_container_width=True)

        # التصدير كـ CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Fuel History (CSV)", csv, "fuel_data.csv", "text/csv")
