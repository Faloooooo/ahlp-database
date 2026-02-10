import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات والروابط ---
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
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == "AHLP2026":
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 3. واجهة التحكم ---
mode = st.sidebar.radio("القائمة الرئيسية:", ["📊 التقارير", "✍️ إدخال البيانات"])

if mode == "✍️ إدخال البيانات":
    st.header("✍️ تسجيل البيانات اليومية")
    cat = st.selectbox("الفئة:", ["المازوت (Fuel)", "المياه (Water)"])
    with st.form("entry_form", clear_on_submit=True):
        if cat == "المازوت (Fuel)":
            c1, c2 = st.columns(2)
            m = c1.number_input("Emergency (cm)", min_value=0.0)
            r = c2.number_input("Receiving (cm)", min_value=0.0)
            d = c1.number_input("Daily (cm)", min_value=0.0)
            b = c2.number_input("Boiler (cm)", min_value=0.0)
            bl = st.number_input("Bought Liters (كمية الشراء باللتر)")
            bp = st.number_input("Total Price USD (السعر الإجمالي)")
            vals, s_name = [m, r, d, b, bl, bp], "Fuel_Data"
        else:
            col1, col2 = st.columns(2)
            with col1:
                tc = st.number_input("Truck Count (عدد الصهاريج)", step=1)
                ts = st.number_input("Truck Size M3 (حجم الصهريج)", value=20.0)
                tp = st.number_input("Truck Cost (سعر الصهاريج)")
            with col2:
                cw = st.number_input("City Meter (عداد الدولة)")
                cb = st.number_input("City Bill (فاتورة الدولة)")
                of = st.number_input("Other Fees (رسوم أخرى)")
            vals, s_name = [cw, tc, ts, tp, cb, of], "Water_Data"
        
        if st.form_submit_button("🚀 إرسال البيانات"):
            if send_to_google(s_name, vals): st.success("✅ تم حفظ البيانات بنجاح")
            else: st.error("❌ فشل الاتصال بقاعدة البيانات")

else:
    report = st.sidebar.selectbox("نوع التقرير:", ["تقرير المازوت", "تحليل المياه"])
    c_d1, c_d2 = st.columns(2)
    sd, ed = c_d1.date_input("من تاريخ", datetime.now()-timedelta(7)), c_d2.date_input("إلى تاريخ", datetime.now())

    if report == "تقرير المازوت":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)]
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                
                # --- القسم المطلوب: كم صرفت من آخر بيانات ---
                if len(df) >= 2:
                    st.subheader("📉 الاستهلاك منذ آخر تحديث (باللتر)")
                    prev = df.iloc[-2]
                    c = st.columns(4)
                    
                    def get_usage(curr, pre, factor):
                        diff = float(pre) - float(curr)
                        return diff * factor if diff
