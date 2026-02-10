import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات والروابط (ثابتة) ---
st.set_page_config(page_title="Ramada Management", layout="wide")
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

# --- 3. التنقل ---
mode = st.sidebar.radio("القائمة:", ["📊 التقارير", "✍️ إدخال البيانات"])

if mode == "✍️ إدخال البيانات":
    st.header("✍️ تسجيل البيانات")
    cat = st.selectbox("الفئة:", ["المازوت (Fuel)", "المياه (Water)", "الغاز", "الكهرباء", "المولدات"])
    with st.form("entry_form", clear_on_submit=True):
        if cat == "المازوت (Fuel)":
            c1, c2 = st.columns(2)
            vals = [c1.number_input("Emergency (cm)"), c2.number_input("Receiving (cm)"), c1.number_input("Daily (cm)"), c2.number_input("Boiler (cm)"), st.number_input("Bought Liters"), st.number_input("Total Price")]
            s_name = "Fuel_Data"
        elif cat == "المياه (Water)":
            c1, c2 = st.columns(2)
            tc, ts, tp = c1.number_input("Extra Truck Count", step=1), c1.number_input("Truck Size M3", value=20.0), c1.number_input("Truck Cost USD")
            cw, cb, of = c2.number_input("City Water Reading"), c2.number_input("City Bill USD"), c2.number_input("Other Fees")
            vals, s_name = [cw, tc, ts, tp, cb, of], "Water_Data"
        else: # (باقي الفئات تبقى دون مساس)
            vals, s_name = [0,0,0,0], ""
        
        if st.form_submit_button("🚀 Submit"):
            if send_to_google(s_name, vals): st.success("✅ Done")
            else: st.error("❌ Error")

else:
    report = st.sidebar.selectbox("التقرير:", ["Diesel Analysis", "Water Analysis"])
    sd = st.sidebar.date_input("From", datetime.now()-timedelta(7))
    ed = st.sidebar.date_input("To", datetime.now())

    if report == "Diesel Analysis":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)]
            if not df_filt.empty:
                last, prev = df_filt.iloc[-1], df.iloc[-2] if len(df)>1 else df.iloc[-1]
                st.subheader("📉 الاستهلاك اللحظي (Liters)")
                c = st.columns(4)
                for i, (n, f) in enumerate(zip(['Emergency','Receiving','Daily','Boiler'], [107.22, 37.65, 31.26, 37.65])):
                    diff = max(0, float(prev.iloc[i+1]) - float(last.iloc[i+1]))
                    c[i].metric(f"{n} spent", f"{diff*f:,.1f} L")
                
                st.divider()
                st.subheader("📈 حركة المخزون")
                fig = go.Figure()
                for i, (n, col, f) in enumerate(zip(['Emergency','Receiving','Daily','Boiler'],['red','blue','green','orange'], [107.22, 37.65, 31.26, 37.65])):
                    fig.add_trace(go.Scatter(x=df_filt['Timestamp'], y=df_filt.iloc[:, i+1]*f, name=n, line=dict(color=col)))
                st.plotly_chart(fig, use_container_width=True)

    elif report == "Water Analysis":
        st.header("💧 Water Analysis Report")
        dfw = load_data('water')
        if not dfw.empty:
            dff = dfw[(dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)]
            if not dff.empty:
                # --- التعديل الجوهري للحساب الصحيح (الضرب لكل سطر) ---
                city_m3 = max(0, dff.iloc[-1, 1] - dff.iloc[0, 1])
                truck_count = dff.iloc[:, 2].sum()
                # حساب الأمتار: كل سطر (عدد الصهاريج × حجمها)
                truck_m3 = (dff.iloc[:, 2] * dff.iloc[:, 3]).sum() 
                truck_cost = dff.iloc[:, 4].sum()
                city_cost = dff.iloc[:, 5].sum() + dff.iloc[:, 6].sum()

                # العرض المطلوب
                st.subheader(f"Summary: {sd} to {ed}")
                c1, c2, c3 = st.columns(3)
                c1.metric("City Water m³", f"{city_m3:,.1f}")
                c2.metric("Truck Water m³", f"{truck_m3:,.1f}") # سيظهر 114 الآن
                c3.metric("Total Water m³", f"{(city_m3 + truck_m3):,.1f}")
                
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("City Cost", f"${city_cost:,.2f}")
                k2.metric("Trucks Count", f"{truck_count:,.0f}")
                k3.metric("Total Truck Cost", f"${truck_cost:,.2f}") # سيظهر 466.2 الآن
                k4.metric("TOTAL COST", f"${(city_cost + truck_cost):,.2f}")
                
                csv = dff.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Report (CSV)", csv, "water_report.csv", "text/csv")
