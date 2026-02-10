import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات ---
st.set_page_config(page_title="Ramada Management System", layout="wide")

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
mode = st.sidebar.radio("القائمة:", ["📊 التقارير", "✍️ إدخال البيانات"])

if mode == "✍️ إدخال البيانات":
    st.header("✍️ تسجيل البيانات")
    category = st.selectbox("الفئة:", ["المازوت (Fuel)", "المياه (Water)", "الغاز (Gas)", "الكهرباء (EDL)", "المولدات (5)"])
    with st.form("entry_form"):
        if category == "المازوت (Fuel)":
            c1, c2 = st.columns(2)
            v = [c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)"), c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)"), st.number_input("Liters Bought"), st.number_input("Price USD")]
            s_name = "Fuel_Data"
        elif category == "المياه (Water)":
            c1, c2 = st.columns(2)
            v = [c2.number_input("City Meter"), c1.number_input("Truck Count", step=1), c1.number_input("Size M3", value=20.0), c1.number_input("Truck Cost"), c2.number_input("City Bill"), c2.number_input("Other Fees")]
            s_name = "Water_Data"
        elif category == "الغاز (Gas)":
            c1, c2 = st.columns(2)
            v = [c1.number_input("Tank %"), c1.number_input("Cylinders"), c2.number_input("Bought L"), c2.number_input("Price USD")]
            s_name = "Gas_Data"
        elif category == "الكهرباء (EDL)":
            c1, c2 = st.columns(2)
            v = [c1.number_input("Night"), c1.number_input("Peak"), c2.number_input("Day"), c2.number_input("Bill USD")]
            s_name = "Electricity_Accrual"
        elif category == "المولدات (5)":
            v = []
            for i in range(1, 6):
                c1, c2 = st.columns(2)
                v.extend([c1.number_input(f"kWh G{i}"), c2.number_input(f"SMU G{i}")])
            s_name = "Generators_kwh"
        
        if st.form_submit_button("🚀 حفظ"):
            if send_to_google(s_name, v): st.success("✅ تم")
            else: st.error("❌ خطأ")

else:
    report = st.sidebar.selectbox("التقرير:", ["تقرير المازوت", "تحليل المياه"])
    sd, ed = st.sidebar.date_input("من", datetime.now()-timedelta(7)), st.sidebar.date_input("إلى", datetime.now())

    if report == "تقرير المازوت":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)]
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else last
                
                # السطر الأول: الكميات الحالية (الموجود في الخزان)
                st.subheader("📍 المخزون الحالي في الخزانات (Liters)")
                c = st.columns(4)
                lbls = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                fcts = [107.22, 37.6572, 31.26, 37.6572]
                for i in range(4):
                    c[i].metric(lbls[i], f"{float(last.iloc[i+1])*fcts[i]:,.0f} L")
                
                # السطر الثاني: المصرف الحالي (الفرق بين آخر قراءتين)
                st.divider()
                st.subheader("📉 المصرف من آخر بيانات (Liters)")
                cs = st.columns(4)
                for i in range(4):
                    diff = max(0, float(prev.iloc[i+1]) - float(last.iloc[i+1]))
                    cs[i].metric(f"{lbls[i]} Spent", f"{diff*fcts[i]:,.1f} L", delta_color="inverse")

                # الرسم البياني
                st.divider()
                fig = go.Figure()
                clrs = ['red', 'blue', 'green', 'orange']
                for i in range(4):
                    fig.add_trace(go.Scatter(x=df_filt['Timestamp'], y=df_filt.iloc[:, i+1]*fcts[i], name=lbls[i], line=dict(color=clrs[i])))
                st.plotly_chart(fig, use_container_width=True)

    elif report == "تحليل المياه":
        dfw = load_data('water')
        if not dfw.empty:
            dff = dfw[(dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)]
            if not dff.empty:
                st.header("💧 تقرير المياه")
                city_m3 = max(0, float(dff.iloc[-1, 1]) - float(dff.iloc[0, 1]))
                truck_m3 = (dff.iloc[:, 2].astype(float) * dff.iloc[:, 3].astype(float)).sum()
                truck_cost = dff.iloc[:, 4].astype(float).sum()
                city_cost = dff.iloc[:, 5].astype(float).sum() + dff.iloc[:, 6].astype(float).sum()
                
                res = st.columns(3)
                res[0].metric("مياه الدولة m³", f"{city_m3:,.1f}")
                res[1].metric("مياه الصهاريج m³", f"{truck_m3:,.1f}")
                res[2].metric("الإجمالي m³", f"{(city_m3 + truck_m3):,.1f}")
                
                cost = st.columns(3)
                cost[0].metric("تكلفة الدولة", f"${city_cost:,.2f}")
                cost[1].metric("تكلفة الصهاريج", f"${truck_cost:,.2f}")
                cost[2].metric("الإجمالي USD", f"${(city_cost + truck_cost):,.2f}")
