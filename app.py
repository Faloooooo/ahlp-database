import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات والروابط ---
st.set_page_config(page_title="Ramada Management System", layout="wide", page_icon="🏨")

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
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
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
        if st.button("Login"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 3. القائمة الجانبية ---
mode = st.sidebar.radio("القائمة الرئيسية:", ["📊 التقارير التشغيلية", "✍️ إدخال البيانات اليومية"])

# ==========================================
# ✍️ قسم إدخال البيانات (تمت إعادة كافة الصفحات)
# ==========================================
if mode == "✍️ إدخال البيانات اليومية":
    st.header("✍️ تسجيل البيانات اليومية")
    category = st.selectbox("الفئة:", ["المازوت (Fuel)", "المياه (Water)", "الغاز (Gas)", "كهرباء الدولة (EDL)", "المولدات (Generators)"])
    
    with st.form("entry_form", clear_on_submit=True):
        if category == "المازوت (Fuel)":
            c1, c2 = st.columns(2)
            vals = [c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)"), 
                    c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)"),
                    st.number_input("Bought Liters (كمية الشراء)"), st.number_input("Price USD")]
            s_name = "Fuel_Data"

        elif category == "المياه (Water)":
            c1, c2 = st.columns(2)
            tc, ts, tp = c1.number_input("Extra Truck Count", step=1), c1.number_input("Truck Size M3", value=20.0), c1.number_input("Truck Cost USD")
            cw, cb, of = c2.number_input("City Water Reading"), c2.number_input("City Bill USD"), c2.number_input("Other Fees")
            vals, s_name = [cw, tc, ts, tp, cb, of], "Water_Data"

        elif category == "الغاز (Gas)":
            vals, s_name = [st.number_input("النسبة المئوية في الخزان %"), st.number_input("كمية الشراء (لتر)"), 0, 0], "Gas_Data"

        elif category == "كهرباء الدولة (EDL)":
            vals, s_name = [st.number_input("Night"), st.number_input("Peak"), st.number_input("Day"), st.number_input("Total Bill USD")], "Electricity_Accrual"

        elif category == "المولدات (Generators)":
            v = []
            for i in range(1, 4):
                col1, col2 = st.columns(2)
                v.extend([col1.number_input(f"kWh G{i}"), col2.number_input(f"SMU G{i}")])
            vals, s_name = v, "Generators_kwh"

        if st.form_submit_button("🚀 إرسال البيانات"):
            if send_to_google(s_name, vals): st.success("✅ تم حفظ البيانات بنجاح")
            else: st.error("❌ فشل في الإرسال")

# ==========================================
# 📊 قسم التقارير (إصلاح المازوت وتثبيت المياه)
# ==========================================
else:
    report = st.sidebar.selectbox("نوع التقرير:", ["تقرير المازوت", "تقرير المياه (المطور)"])
    sd = st.sidebar.date_input("من تاريخ", datetime.now()-timedelta(7))
    ed = st.sidebar.date_input("إلى تاريخ", datetime.now())

    if report == "تقرير المازوت":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)]
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                
                # --- الاستهلاك منذ آخر تحديث ---
                if len(df) >= 2:
                    st.subheader("📉 الاستهلاك منذ آخر تحديث (باللتر)")
                    prev = df.iloc[-2]
                    c = st.columns(4)
                    def calc(p, c, f): return max(0, float(p) - float(c)) * f
                    c[0].metric("Emergency spent", f"{calc(prev.iloc[1], last.iloc[1], CONV['main']):,.1f} L")
                    c[1].metric("Receiving spent", f"{calc(prev.iloc[2], last.iloc[2], CONV['rec']):,.1f} L")
                    c[2].metric("Daily spent", f"{calc(prev.iloc[3], last.iloc[3], CONV['daily']):,.1f} L")
                    c[3].metric("Boiler spent", f"{calc(prev.iloc[4], last.iloc[4], CONV['boil']):,.1f} L")

                # --- إعادة خطوط الكمية في الرسم البياني ---
                st.divider()
                st.subheader("📈 مستويات المخزون في الخزانات الأربعة")
                fig = go.Figure()
                clrs = ['red', 'blue', 'green', 'orange']
                lbls = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                fcts = [CONV['main'], CONV['rec'], CONV['daily'], CONV['boil']]
                for i in range(4):
                    fig.add_trace(go.Scatter(x=df_filt['Timestamp'], y=df_filt.iloc[:, i+1]*fcts[i], name=lbls[i], line=dict(color=clrs[i], width=2)))
                fig.update_layout(hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

    elif report == "تقرير المياه (المطور)":
        dfw = load_data('water')
        if not dfw.empty:
            dff = dfw[(dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)]
            if not dff.empty:
                st.header("💧 نتائج تحليل المياه")
                city_m3 = max(0, dff.iloc[-1, 1] - dff.iloc[0, 1])
                truck_m3 = (dff.iloc[:, 2] * dff.iloc[:, 3]).sum() 
                truck_cost = dff.iloc[:, 4].sum()
                city_cost = dff.iloc[:, 5].sum() + dff.iloc[:, 6].sum()

                c1, c2, c3 = st.columns(3)
                c1.metric("مياه الدولة m³", f"{city_m3:,.1f}")
                c2.metric("مياه الصهاريج m³", f"{truck_m3:,.1f}")
                c3.metric("المجموع العام m³", f"{(city_m3 + truck_m3):,.1f}")
                
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("تكلفة الدولة", f"${city_cost:,.2f}")
                k2.metric("عدد الصهاريج", f"{dff.iloc[:, 2].sum():,.0f}")
                k3.metric("تكلفة الصهاريج", f"${truck_cost:,.2f}")
                k4.metric("الإجمالي USD", f"${(city_cost + truck_cost):,.2f}")
