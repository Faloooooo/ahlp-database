import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات والروابط ---
st.set_page_config(page_title="Ramada Plaza System", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'water': '423939923', 'gas': '578874363', 'electricity': '1588872380', 'generators': '1679289485'}
CONV = [107.22, 37.6572, 31.26, 37.6572]

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

# --- 2. نظام الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"): st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 3. القائمة ---
mode = st.sidebar.radio("القائمة:", ["📊 التقارير", "✍️ إدخال البيانات"])

if mode == "✍️ إدخال البيانات":
    st.header("✍️ تسجيل البيانات اليومية")
    cat = st.selectbox("الفئة:", ["المازوت", "المياه", "الغاز", "الكهرباء", "المولدات"])
    with st.form("entry_f"):
        if cat == "المازوت":
            c1, c2 = st.columns(2)
            v = [c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)"), c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)"), st.number_input("Liters Bought"), st.number_input("Price USD")]
            s_name = "Fuel_Data"
        elif cat == "المياه":
            c1, c2 = st.columns(2)
            v = [c2.number_input("City Meter"), c1.number_input("Truck Count"), c1.number_input("Size M3"), c1.number_input("Cost"), c2.number_input("City Bill"), c2.number_input("Other Fees")]
            s_name = "Water_Data"
        # باقي الفئات بنفس التنسيق البسيط
        elif cat == "الغاز": v = [st.number_input("Tank %"), st.number_input("Cylinders"), st.number_input("Liters"), st.number_input("Price")]; s_name = "Gas_Data"
        elif cat == "الكهرباء": v = [st.number_input("Night"), st.number_input("Peak"), st.number_input("Day"), st.number_input("Bill")]; s_name = "Electricity_Accrual"
        elif cat == "المولدات":
            v = []
            for i in range(1, 6): v.extend([st.number_input(f"kWh G{i}"), st.number_input(f"SMU G{i}")])
            s_name = "Generators_kwh"
        
        if st.form_submit_button("🚀 حفظ"):
            if send_to_google(s_name, v): st.success("✅ تم")
            else: st.error("❌ فشل")

else:
    report = st.sidebar.selectbox("التقرير:", ["المازوت", "المياه"])
    sd, ed = st.sidebar.date_input("من", datetime.now()-timedelta(1)), st.sidebar.date_input("إلى", datetime.now())

    if report == "المازوت":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)].sort_values('Timestamp')
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                first = df_filt.iloc[0]
                price = float(df.iloc[-1, 6]) if not pd.isna(df.iloc[-1, 6]) else 0
                
                # المخزون الحالي
                st.subheader("📍 المخزون الحالي (Liters)")
                c = st.columns(4)
                lbls = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                total_s = 0
                for i in range(4):
                    val = float(last.iloc[i+1]) * CONV[i]
                    total_s += val
                    c[i].metric(lbls[i], f"{val:,.0f} L")
                st.info(f"💰 قيمة المخزون: **${(total_s * price / 1000):,.2f}**")

                # المصرف الإجمالي
                st.divider()
                st.subheader(f"📉 المصرف الإجمالي ({sd} إلى {ed})")
                cs = st.columns(4)
                total_v = 0
                for i in range(4):
                    usage = max(0, float(first.iloc[i+1]) - float(last.iloc[i+1]))
                    liters = usage * CONV[i]
                    total_v += liters
                    cs[i].metric(f"{lbls[i]} Spent", f"{liters:,.1f} L")
                st.warning(f"💵 تكلفة المصرف: **${(total_v * price / 1000):,.2f}**")

    elif report == "المياه":
        dfw = load_data('water')
        if not dfw.empty:
            dff = dfw[(dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)]
            if not dff.empty:
                st.header("💧 تقرير المياه")
                city_m3 = max(0, float(dff.iloc[-1, 1]) - float(dff.iloc[0, 1]))
                truck_m3 = (dff.iloc[:, 2].astype(float) * dff.iloc[:, 3].astype(float)).sum()
                truck_c = dff.iloc[:, 4].astype(float).sum()
                city_c = dff.iloc[:, 5].astype(float).sum() + dff.iloc[:, 6].astype(float).sum()
                r1 = st.columns(3); r1[0].metric("دولة m³", f"{city_m3:,.1f}"); r1[1].metric("صهاريج m³", f"{truck_m3:,.1f}"); r1[2].metric("إجمالي m³", f"{(city_m3+truck_m3):,.1f}")
                r2 = st.columns(3); r2[0].metric("تكلفة دولة", f"${city_c:,.2f}"); r2[1].metric("تكلفة صهاريج", f"${truck_c:,.2f}"); r2[2].metric("إجمالي $", f"${(city_c+truck_c):,.2f}")
