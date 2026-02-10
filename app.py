import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات الأساسية ---
st.set_page_config(page_title="Ramada Management", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'water': '423939923'}
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

# --- 2. تسجيل الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"): st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 3. واجهة التحكم ---
mode = st.sidebar.radio("Main Menu:", ["📊 Reports", "✍️ Data Entry"])

if mode == "✍️ Data Entry":
    st.header("✍️ Record Daily Data")
    cat = st.selectbox("Category:", ["Diesel (Fuel)", "Water"])
    with st.form("entry_form", clear_on_submit=True):
        if cat == "Diesel (Fuel)":
            c1, c2 = st.columns(2)
            m, r = c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)")
            d, b = c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)")
            bl, bp = st.number_input("Bought Liters"), st.number_input("Total Price USD")
            vals, s_name = [m, r, d, b, bl, bp], "Fuel_Data"
        else:
            c1, c2 = st.columns(2)
            tc, ts, tp = c1.number_input("Truck Count"), c1.number_input("Truck Size M3"), c1.number_input("Truck Cost")
            cw, cb, of = c2.number_input("City Meter"), c2.number_input("City Bill"), c2.number_input("Other Fees")
            vals, s_name = [cw, tc, ts, tp, cb, of], "Water_Data"
        
        if st.form_submit_button("Submit"):
            if send_to_google(s_name, vals): st.success("✅ Success")
            else: st.error("❌ Failed")

else:
    report = st.sidebar.selectbox("Choose Report:", ["Diesel Report", "Water Analysis"])
    c_d1, c_d2 = st.columns(2)
    sd, ed = c_d1.date_input("From", datetime.now()-timedelta(7)), c_d2.date_input("To", datetime.now())

    if report == "Diesel Report":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)]
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                
                # --- القسم المطلوب: كم صرفت من آخر بيانات ---
                if len(df) >= 2:
                    st.subheader("📉 Consumption (Liters) - Last Update")
                    prev = df.iloc[-2]
                    c = st.columns(4)
                    
                    def get_usage(curr, pre, factor):
                        diff = pre - curr
                        return diff * factor if diff > 0 else 0.0

                    # إصلاح الخطأ البرمجي في f-string
                    c[0].metric("Emergency spent", f"{get_usage(last.iloc[1], prev.iloc[1], CONV['main']):,.1f} L")
                    c[1].metric("Receiving spent", f"{get_usage(last.iloc[2], prev.iloc[2], CONV['rec']):,.1f} L")
                    c[2].metric("Daily spent", f"{get_usage(last.iloc[3], prev.iloc[3], CONV['daily']):,.1f} L")
                    c[3].metric("Boiler spent", f"{get_usage(last.iloc[4], prev.iloc[4], CONV['boil']):,.1f} L")

                # --- المخزون الحالي ---
                st.divider()
                st.subheader("📍 Current Stock")
                m = st.columns(4)
                m[0].metric("Emergency", f"{last.iloc[1]*CONV['main']:,.0f} L")
                m[1].metric("Receiving", f"{last.iloc[2]*CONV['rec']:,.0f} L")
                m[2].metric("Daily", f"{last.iloc[3]*CONV['daily']:,.0f} L")
                m[3].metric("Boiler", f"{last.iloc[4]*CONV['boil']:,.0f} L")

                # --- الرسم البياني (إصلاح KeyError) ---
                fig = go.Figure()
                clrs = ['red', 'blue', 'green', 'orange']
                lbls = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                fcts = [CONV['main'], CONV['rec'], CONV['daily'], CONV['boil']]
                for i in range(4):
                    fig.add_trace(go.Scatter(x=df_filt['Timestamp'], y=df_filt.iloc[:, i+1]*f
