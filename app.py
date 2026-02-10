import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات ---
st.set_page_config(page_title="Ramada Management", layout="wide")
SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'water': '423939923'}
# معاملات التحويل سم إلى لتر
CONV = {'main': 107.22, 'rec': 37.6572, 'daily': 31.26, 'boil': 37.6572}

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip()
        if 'Timestamp' in df.columns: df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except: return pd.DataFrame()

# --- 2. الدخول والقائمة ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"): st.session_state.authenticated = True; st.rerun()
    st.stop()

mode = st.sidebar.radio("Main Menu:", ["📊 Reports", "✍️ Data Entry"])

if mode == "✍️ Data Entry":
    st.header("✍️ Record Daily Data")
    # (هنا تبقى صفحة الإدخال كما هي تماماً بدون أي تغيير)
    st.info("قم بإدخال البيانات كالمعتاد وسيقوم التقرير بحساب الصرف تلقائياً.")
    # ... كود الإدخال المختصر هنا ...

else:
    report = st.sidebar.selectbox("Choose Report:", ["Diesel Analysis", "Water Analysis"])
    c_d1, c_d2 = st.columns(2)
    sd, ed = c_d1.date_input("From", datetime.now()-timedelta(7)), c_d2.date_input("To", datetime.now())

    if report == "Diesel Analysis":
        df = load_data('fuel')
        if not df.empty:
            df_filtered = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)]
            
            if not df_filtered.empty:
                last = df_filtered.iloc[-1]
                
                # --- القسم الذي سألت عنه: كم صرفت من آخر بيانات ---
                if len(df) >= 2:
                    st.subheader("📉 كم صرفت من آخر بيانات (Liters)")
                    prev = df.iloc[-2] # السطر قبل الأخير
                    
                    # دالة ذكية تحسب الفرق (فقط إذا كان نقصاً لمعالجة النقل)
                    def calc_spent(p, c, f):
                        diff = p - c
                        return diff * f if diff > 0 else 0.0

                    c1, c2, c3, c4 = st.columns(4)
                    spent_m = calc_spent(prev.iloc[1], last.iloc[1], CONV['main'])
                    spent_r = calc_spent(prev.iloc[2], last.iloc[2], CONV['rec'])
                    spent_d = calc_spent(prev.iloc[3], last.iloc[3], CONV['daily'])
                    spent_b = calc_spent(prev.iloc[4], last.iloc[4], CONV['boil'])
                    
                    c1.metric("Emergency spent", f"{spent_m:,.1f} L")
                    c2.metric("Receiving spent", f"{spent_r:,.1f} L")
                    c3.metric("Daily spent", f"{spent_d:,.1f} L")
                    c4.metric("Boiler spent", f"{spent_b:,.
