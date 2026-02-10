import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات ---
st.set_page_config(page_title="Ramada Plaza System", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'water': '423939923', 'gas': '578874363', 'electricity': '1588872380', 'generators': '1679289485'}
CONV = {'main': 107.22, 'rec': 37.6572, 'daily': 31.26, 'boil': 37.6572}

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip()
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        return df
    except: return pd.DataFrame()

def send_to_google(sheet_name, values):
    try:
        payload = json.dumps({"sheet": sheet_name, "values": values})
        response = requests.post(SCRIPT_URL, data=payload, headers={"Content-Type": "application/json"})
        return response.status_code == 200
    except: return False

# --- 2. الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"): st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 3. التنقل ---
mode = st.sidebar.radio("القائمة:", ["📊 التقارير", "✍️ الإدخال"])

if mode == "✍️ الإدخال":
    st.header("✍️ تسجيل البيانات")
    cat = st.selectbox("الفئة:", ["المازوت", "المياه", "الغاز", "الكهرباء", "المولدات (5)"])
    with st.form("f1", clear_on_submit=True):
        if cat == "المازوت":
            c1, c2 = st.columns(2)
            vals = [c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)"), c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)"), st.number_input("Liters"), st.number_input("Price")]
            s_name = "Fuel_Data"
        elif cat == "المياه":
            c1, c2 = st.columns(2)
            tc, ts, tp = c1.number_input("Extra Truck Count", step=1), c1.number_input("Size M3", value=20.0), c1.number_input("Cost USD")
            cw, cb, of = c2.number_input("City Meter"), c2.number_input("City Bill"), c2.number_input("Other Fees")
            vals, s_name = [cw, tc, ts, tp, cb, of], "Water_Data"
        elif cat == "الغاز":
            c1, c2 = st.columns(2)
            vals = [c1.number_input("Tank %"), c1.number_input("Cylinders"), c2.number_input("Bought L"), c2.number_input("Price USD")]
            s_name = "Gas_Data"
        elif cat == "الكهرباء":
            c1, c2 = st.columns(2)
            vals = [c1.number_input("Night"), c1.number_input("Peak"), c2.number_input("Day"), c2.number_input("Bill USD")]
            s_name = "Electricity_Accrual"
        elif cat == "المولدات (5)":
            v = []
            for i in range(1, 6):
                col1, col2 = st.columns(2)
                v.extend([col1.number_input(f"kWh G{i}"), col2.number_input(f"SMU G{i}")])
            vals, s_name = v, "Generators_kwh"
        
        if st.form_submit_button("🚀 حفظ"):
            if send_to_google(s_name, vals): st.success("✅ تم")
            else: st.error("❌ خطأ")

else:
    report = st.sidebar.selectbox("التقرير:", ["المازوت", "المياه"])
    sd, ed = st.sidebar.date_input("من", datetime.now()-timedelta(7)), st.sidebar.date_input("إلى", datetime.now())

    if report == "المازوت":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)]
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                st.subheader("📍 المخزون الحالي (لتر)")
                c = st.columns(4)
                fcts = [CONV['main'], CONV['rec'], CONV['daily'], CONV['boil']]
                lbls = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                clrs = ['red', 'blue', 'green', 'orange']
                for i in range(4):
                    c[i].metric(lbls[i], f"{last.iloc[i+1]*fcts[i]:,.0f} L")
                
                fig = go.Figure()
                for i in range(4):
                    fig.add_trace(go.Scatter(x=df_filt['Timestamp'], y=df_filt.iloc[:, i+1]*fcts[i], name=lbls[i], line=dict(color=clrs[i])))
                st.plotly_chart(fig, use_container_width=True)

    elif report == "المياه":
        dfw = load_data('water')
        if not dfw.empty:
            dff = dfw[(dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)]
            if not dff.empty:
                st.header("💧 تقرير المياه")
                city_m3 = max(0, dff.iloc[-1, 1] - dff.iloc[0, 1])
                truck_m3 = (dff.iloc[:, 2] * dff.iloc[:,
