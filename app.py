import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات والروابط ---
st.set_page_config(page_title="Ramada Plaza Management", layout="wide", page_icon="🏨")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'water': '423939923', 'gas': '578874363', 'electricity': '1588872380', 'generators': '1679289485'}
CONV = {'main': 107.22, 'rec': 37.6572, 'daily': 31.26, 'boil': 37.6572}

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip()
        if 'Timestamp' in df.columns: df['Timestamp'] = pd.to_datetime(df['Timestamp'])
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

# --- 3. القائمة الجانبية ---
mode = st.sidebar.radio("القائمة الرئيسية:", ["📊 التقارير", "✍️ إدخال البيانات"])

# ==========================================
# ✍️ قسم إدخال البيانات (تم تعديله حسب طلبك)
# ==========================================
if mode == "✍️ إدخال البيانات":
    st.header("✍️ تسجيل البيانات اليومية")
    cat = st.selectbox("الفئة:", ["المازوت (Fuel)", "المياه (Water)", "الغاز (Gas)", "الكهرباء (EDL)", "المولدات (5 Generators)"])
    
    with st.form("entry_form", clear_on_submit=True):
        if cat == "المازوت (Fuel)":
            c1, c2 = st.columns(2)
            m, r = c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)")
            d, b = c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)")
            bl, bp = st.number_input("Bought Liters"), st.number_input("Price USD")
            vals, s_name = [m, r, d, b, bl, bp], "Fuel_Data"

        elif cat == "المياه (Water)":
            c1, c2 = st.columns(2)
            tc, ts, tp = c1.number_input("Extra Truck Count", step=1), c1.number_input("Truck Size M3", value=20.0), c1.number_input("Truck Cost USD")
            cw, cb, of = c2.number_input("City Meter Reading"), c2.number_input("City Bill USD"), c2.number_input("Other Fees")
            vals, s_name = [cw, tc, ts, tp, cb, of], "Water_Data"

        elif cat == "الغاز (Gas)":
            c1, c2 = st.columns(2)
            perc = c1.number_input("النسبة المئوية في الخزان %")
            btl = c1.number_input("عدد قناني الغاز (Cylinders)", step=1)
            buy_l = c2.number_input("كمية الشراء (لتر)")
            price = c2.number_input("سعر القناني/الشراء USD")
            vals, s_name = [perc, btl, buy_l, price], "Gas_Data"

        elif cat == "الكهرباء (EDL)":
            c1, c2 = st.columns(2)
            n = c1.number_input("Night Reading")
            p = c1.number_input("Peak Reading")
            d = c2.number_input("Day Reading")
            bill = c2.number_input("Total Bill USD")
            vals, s_name = [n, p, d, bill], "Electricity_Accrual"

        elif cat == "المولدات (5 Generators)":
            v = []
            for i in range(1, 6): # من المولد 1 إلى 5
                st.subheader(f"Generator {i}")
                c1, c2 = st.columns(2)
                v.extend([c1.number_input(f"kWh G{i}", key=f"k{i}"), c2.number_input(f"SMU G{i}", key=f"s{i}")])
            vals, s_name = v, "Generators_kwh"

        if st.form_submit_button("🚀 حفظ البيانات"):
            if send_to_google(s_name, vals): st.success("✅ تم الحفظ بنجاح")
            else: st.error("❌ فشل في الإرسال")

# ==========================================
# 📊 قسم التقارير (المازوت والمياه)
# ==========================================
else:
    report = st.sidebar.selectbox("نوع التقرير:", ["تقرير المازوت", "تحليل المياه"])
    sd, ed = st.sidebar.date_input("من", datetime.now()-timedelta(7)), st.sidebar.date_input("إلى", datetime.now())

    if report == "تقرير المازوت":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)]
            if not df_filt.empty:
                last, prev = df_filt.iloc[-1], df.iloc[-2] if len(df)>1 else df.iloc[-1]
                st.subheader("📉 الصرف منذ آخر قراءة (باللتر)")
                c = st.columns(4)
                fcts = [CONV['main'], CONV['rec'], CONV['daily'], CONV['boil']]
                names = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                for i in range(4):
                    diff = max(0, float(prev.iloc[i+1]) - float(last.iloc[i+1]))
                    c[i].metric(f"{names[i]} Spent", f"{diff*fcts[i]:,.1f} L")
                
                st.divider()
                st.subheader("📈 مستويات الخزانات (خطوط الأربعة)")
                fig = go.Figure()
                clrs = ['red', 'blue', 'green', 'orange']
                for i in range(4):
                    fig.add_trace(go.Scatter(x=df_filt['Timestamp'], y=df_filt.iloc[:, i+1]*fcts[i], name=names[i], line=dict(color=clrs[i])))
                st.plotly_chart(fig, use_container_width=True)

    elif report == "تحليل المياه":
        dfw = load_data('water')
        if not dfw.empty:
            dff = dfw[(dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)]
            if not dff.empty:
                st.header("💧 نتائج تحليل المياه")
