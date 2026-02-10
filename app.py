import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات والروابط ---
st.set_page_config(page_title="Operational Management", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

# روابط الصفحات (GIDs)
GIDS = {'fuel': '1077908569', 'water': '423939923', 'gas': '578874363', 'electricity': '1588872380', 'generators': '1679289485'}
CONV = {'main': 107.22, 'rec': 37.6572, 'daily': 31.26, 'boil': 37.6572}

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip()
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error loading {name}: {e}")
        return pd.DataFrame()

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
        if st.button("Login"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 3. الواجهة الرئيسية ---
mode = st.sidebar.radio("القائمة:", ["📊 التقارير التشغيلية", "✍️ إدخال البيانات اليومية"])

# ==========================================
# ✍️ قسم إدخال البيانات (كامل 100%)
# ==========================================
if mode == "✍️ إدخال البيانات اليومية":
    st.header("✍️ تسجيل البيانات")
    cat = st.selectbox("الفئة:", ["المازوت", "المياه", "الغاز", "الكهرباء", "المولدات"])
    
    with st.form("entry_form", clear_on_submit=True):
        if cat == "المازوت":
            c1, c2 = st.columns(2)
            vals = [c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)"), 
                    c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)"),
                    st.number_input("Bought Liters"), st.number_input("Price USD")]
            s_name = "Fuel_Data"
        elif cat == "المياه":
            c1, c2 = st.columns(2)
            tc, ts, tp = c1.number_input("Extra Truck Count"), c1.number_input("Truck Size M3"), c1.number_input("Cost USD")
            cw, cb, of = c2.number_input("City Meter Reading"), c2.number_input("City Bill USD"), c2.number_input("Other Fees")
            vals, s_name = [cw, tc, ts, tp, cb, of], "Water_Data"
        elif cat == "الغاز":
            c1, c2 = st.columns(2)
            vals = [c1.number_input("نسبة الخزان %"), c1.number_input("عدد القناني"), c2.number_input("شراء لتر"), c2.number_input("السعر USD")]
            s_name = "Gas_Data"
        elif cat == "الكهرباء":
            c1, c2 = st.columns(2)
            vals = [c1.number_input("Night"), c1.number_input("Peak"), c2.number_input("Day"), c2.number_input("Bill USD")]
            s_name = "Electricity_Accrual"
        elif cat == "المولدات":
            v = []
            for i in range(1, 6):
                c1, c2 = st.columns(2)
                v.extend([c1.number_input(f"kWh Generator {i}"), c2.number_input(f"SMU Generator {i}")])
            vals, s_name = v, "Generators_kwh"

        if st.form_submit_button("🚀 حفظ"):
            if send_to_google(s_name, vals): st.success("✅ تم الحفظ")
            else: st.error("❌ فشل الإرسال")

# ==========================================
# 📊 قسم التقارير (ثابت ومضمون)
# ==========================================
else:
    report_type = st.sidebar.selectbox("اختر التقرير:", ["تقرير المازوت", "تحليل المياه"])
    sd = st.sidebar.date_input("من تاريخ", datetime.now() - timedelta(7))
    ed = st.sidebar.date_input("إلى تاريخ", datetime.now())

    if report_type == "تقرير المازوت":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)]
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                st.subheader("📍 مستويات الخزانات الحالية (لتر)")
                m = st.columns(4)
                m[0].metric("Emergency", f"{last.iloc[1]*CONV['main']:,.0f} L")
                m[1].metric("Receiving", f"{last.iloc[2]*CONV['rec']:,.0f} L")
                m[2].metric("Daily", f"{last.iloc[3]*CONV['daily']:,.0f} L")
                m[3].metric("Boiler", f"{last.iloc[4]*CONV['boil']:,.0f} L")
                
                st.divider()
                fig = go.Figure()
                lbls = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                clrs = ['red', 'blue', 'green', 'orange']
                fcts = [CONV['main'], CONV['rec'], CONV['daily'], CONV['boil']]
                for i in range(4):
                    fig.add_trace(go.Scatter(x=df_filt['Timestamp'], y=df_filt.iloc[:, i+1]*fcts[i], name=lbls[i], line=dict(color=clrs[i])))
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("لا توجد بيانات مازوت في هذا التاريخ")

    elif report_type == "تحليل المياه":
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
                c3.metric("الإجمالي m³", f"{(city_m3 + truck_m3):,.1f}")
                
                k1, k2, k3 = st.columns(3)
                k1.metric("تكلفة الدولة", f"${city_cost:,.2f}")
                k2.metric("تكلفة الصهاريج", f"${truck_cost:,.2f}")
                k3.metric("الإجمالي USD", f"${(city_cost + truck_cost):,.2f}")
            else: st.warning("لا توجد بيانات مياه في هذا التاريخ")
