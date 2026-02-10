import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات والروابط الأساسية ---
st.set_page_config(page_title="Ramada Plaza System", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

# روابط الصفحات البرمجية
GIDS = {
    'fuel': '1077908569', 
    'water': '423939923', 
    'gas': '578874363', 
    'electricity': '1588872380', 
    'generators': '1679289485'
}

# عوامل تحويل السنتيمتر إلى لتر
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

# --- 2. نظام الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == "AHLP2026":
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 3. التنقل ---
mode = st.sidebar.radio("القائمة الرئيسية:", ["📊 التقارير", "✍️ إدخال البيانات"])

# ==========================================
# ✍️ قسم إدخال البيانات (تم تثبيت كافة الصفحات)
# ==========================================
if mode == "✍️ إدخال البيانات":
    st.header("✍️ تسجيل البيانات اليومية")
    category = st.selectbox("الفئة:", ["المازوت (Fuel)", "المياه (Water)", "الغاز (Gas)", "الكهرباء (EDL)", "المولدات (5)"])
    
    with st.form("entry_form_clean", clear_on_submit=True):
        if category == "المازوت (Fuel)":
            c1, c2 = st.columns(2)
            m = c1.number_input("Emergency (cm)")
            r = c2.number_input("Receiving (cm)")
            d = c1.number_input("Daily (cm)")
            b = c2.number_input("Boiler (cm)")
            bl = st.number_input("Liters Bought")
            bp = st.number_input("Price USD")
            vals, s_name = [m, r, d, b, bl, bp], "Fuel_Data"

        elif category == "المياه (Water)":
            c1, c2 = st.columns(2)
            tc = c1.number_input("Truck Count", step=1)
            ts = c1.number_input("Size M3", value=20.0)
            tp = c1.number_input("Truck Cost")
            cw = c2.number_input("City Meter Reading")
            cb = c2.number_input("City Bill")
            of = c2.number_input("Other Fees")
            vals, s_name = [cw, tc, ts, tp, cb, of], "Water_Data"

        elif category == "الغاز (Gas)":
            c1, c2 = st.columns(2)
            perc = c1.number_input("Tank %")
            btl = c1.number_input("Cylinders Count")
            buy = c2.number_input("Bought Liters")
            prc = c2.number_input("Price USD")
            vals, s_name = [perc, btl, buy, prc], "Gas_Data"

        elif category == "الكهرباء (EDL)":
            c1, c2 = st.columns(2)
            n, p, d = c1.number_input("Night"), c1.number_input("Peak"), c2.number_input("Day")
            bill = c2.number_input("Total Bill USD")
            vals, s_name = [n, p, d, bill], "Electricity_Accrual"

        elif category == "المولدات (5)":
            v = []
            for i in range(1, 6):
                col1, col2 = st.columns(2)
                v.extend([col1.number_input(f"kWh Gen {i}"), col2.number_input(f"SMU Gen {i}")])
            vals, s_name = v, "Generators_kwh"

        if st.form_submit_button("🚀 حفظ"):
            if send_to_google(s_name, vals): st.success("✅ تم الحفظ بنجاح")
            else: st.error("❌ فشل الاتصال")

# ==========================================
# 📊 قسم التقارير (إصلاح المازوت وتثبيت المياه)
# ==========================================
else:
    report = st.sidebar.selectbox("نوع التقرير:", ["تقرير المازوت", "تحليل المياه"])
    sd = st.sidebar.date_input("من", datetime.now()-timedelta(7))
    ed = st.sidebar.date_input("إلى", datetime.now())

    if report == "تقرير المازوت":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)]
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                # عرض الكميات الأربعة الحالية (إصلاح النقص)
                st.subheader("📍 مستويات الخزانات الحالية (لتر)")
                c = st.columns(4)
                c[0].metric("Emergency", f"{float(last.iloc[1])*CONV['main']:,.0f} L")
                c[1].metric("Receiving", f"{float(last.iloc[2])*CONV['rec']:,.0f} L")
                c[2].metric("Daily", f"{float(last.iloc[3])*CONV['daily']:,.0f} L")
                c[3].metric("Boiler", f"{float(last.iloc[4])*CONV['boil']:,.0f} L")
                
                # الرسم البياني للأربعة خطوط (إصلاح Syntax الخطأ في الصورة)
                st.divider()
                fig = go.Figure()
                lbls = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                clrs = ['red', 'blue', 'green', 'orange']
                for i in range(4):
                    y_vals = df_filt.iloc[:, i+1].astype(float) * list(CONV.values())[i]
                    fig.add_trace(go.Scatter(x=df_filt['Timestamp'], y=y_vals, name=lbls[i], line=dict(color=clrs[i])))
                st.plotly_chart(fig, use_container_width=True)

    elif report == "تحليل المياه":
        dfw = load_data('water')
        if not dfw.empty:
            dff = dfw[(dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)]
            if not dff.empty:
                st.header("💧 نتائج تحليل المياه")
                # الحسابات الصحيحة (إصلاح اختفاء التقرير)
                city_m3 = max(0, float(dff.iloc[-1, 1]) - float(dff.iloc[0, 1]))
                truck_m3 = (dff.iloc[:, 2].astype(float) * dff.iloc[:, 3].astype(float)).sum()
                truck_cost = dff.iloc[:, 4].astype(float).sum()
                city_cost = dff.iloc[:, 5].astype(float).sum() + dff.iloc[:, 6].astype(float).sum()

                c1, c2, c3 = st.columns(3)
                c1.metric("مياه الدولة m³", f"{city_m3:,.1f}")
                c2.metric("مياه الصهاريج m³", f"{truck_m3:,.1f}")
                c3.metric("المجموع m³", f"{(city_m3 + truck_m3):,.1f}")
                
                k1, k2, k3 = st.columns(3)
                k1.metric("تكلفة الدولة", f"${city_cost:,.2f}")
                k2.metric("تكلفة الصهاريج", f"${truck_cost:,.2f}")
                k3.metric("الإجمالي USD", f"${(city_cost + truck_cost):,.2f}")
