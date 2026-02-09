import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import io

# --- 1. إعدادات الصفحة والهوية ---
st.set_page_config(page_title="Ramada Plaza Energy System", layout="wide", page_icon="🏨")

# الروابط المثبتة
SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

# المعرفات ومعاملات التحويل
GIDS = {'fuel': '1077908569', 'gas': '578874363', 'water': '423939923', 'electricity': '1588872380', 'generators': '1679289485'}
CONV = {'main': 107.22, 'rec': 37.6572, 'daily': 31.26, 'boil': 37.6572}

# --- 2. الدوال الأساسية ---
def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip()
        # توحيد أسماء الأعمدة لمنع الأخطاء
        mapping = {'Bought Liters': 'Bought_Liters', 'Total Price (USD)': 'Price_USD'}
        df.rename(columns=mapping, inplace=True)
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except:
        return pd.DataFrame()

def send_to_google(sheet_name, values):
    try:
        payload = json.dumps({"sheet": sheet_name, "values": values})
        response = requests.post(SCRIPT_URL, data=payload, headers={"Content-Type": "application/json"})
        return response.status_code == 200
    except:
        return False

# --- 3. نظام الحماية ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 AHLP System Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == "AHLP2026":
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 4. القائمة الجانبية ---
st.sidebar.title("🏨 Operations Menu")
mode = st.sidebar.radio("Navigation:", ["📊 Intelligence Reports", "✍️ Daily Data Entry"])

# ==========================================
# قسم إدخال البيانات (ترتيب مثبت: مياه، غاز، كهرباء، مازوت، مولدات)
# ==========================================
if mode == "✍️ Daily Data Entry":
    st.header("✍️ Operational Data Recording")
    category = st.selectbox("Utility Category:", ["Water", "Gas (Propane)", "EDL (Electricity)", "Diesel (Fuel)", "Generators"])
    
    with st.form("main_entry_form", clear_on_submit=True):
        if category == "Water":
            st.subheader("🏙️ Water Inventory")
            c1, c2 = st.columns(2)
            cw = c1.number_input("City Meter m³", step=0.1)
            tc = c2.number_input("Trucks Count", step=1)
            ts = c1.number_input("Truck Size m³", value=20.0)
            tp = c2.number_input("Total Trucks Cost (USD)")
            vals, s_name = [cw, tc, ts, tp, 0, 0, 0], "Water_Data"

        elif category == "Gas (Propane)":
            c1, c2 = st.columns(2)
            vals, s_name = [c1.number_input("Tank %"), c2.number_input("Bought Liters"), 
                            c1.number_input("Cylinders Qty"), c2.number_input("Cylinders Cost")], "Gas_Data"

        elif category == "EDL (Electricity)":
            c1, c2 = st.columns(2)
            vals, s_name = [c1.number_input("Night"), c2.number_input("Peak"), 
                            c1.number_input("Day"), c2.number_input("Total Bill USD")], "Electricity_Accrual"

        elif category == "Diesel (Fuel)":
            st.subheader("⛽ Fuel Tank Levels (cm)")
            c1, c2 = st.columns(2)
            m = c1.number_input("Emergency Tank")
            r = c2.number_input("Receiving Tank")
            d = c1.number_input("Daily Tank")
            b = c2.number_input("Boiler Tank")
            st.divider()
            bl = st.number_input("Bought Liters Today")
            bp = st.number_input("Total Purchase Price (USD)")
            vals, s_name = [m, r, d, b, bl, bp], "Fuel_Data"

        elif category == "Generators":
            v = []
            for i in range(1, 4):
                st.write(f"**Generator {i}**")
                col1, col2 = st.columns(2)
                v.extend([col1.number_input(f"kWh G{i}", key=f"k{i}"), col2.number_input(f"SMU G{i}", key=f"s{i}")])
            vals, s_name = v, "Generators_kwh"

        if st.form_submit_button("🚀 Submit to Database"):
            if send_to_google(s_name, vals):
                st.success("✅ Recorded Successfully in Google Sheets")
            else:
                st.error("❌ Transmission Error")

# ==========================================
# قسم التقارير (ذكاء اصطناعي لمعالجة النقل بين الخزانات)
# ==========================================
else:
    st.header("📊 Energy Intelligence Dashboard")
    df = load_data('fuel')
    
    if not df.empty:
        # تأمين الأعمدة الأساسية
        for col in ['Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm', 'Bought_Liters']:
            if col not in df.columns: df[col] = 0.0

        last = df.iloc[-1]
        st.subheader("📍 Current Inventory Status (Liters)")
        m = st.columns(4)
        v_m, v_r, v_d, v_b = last['Main_Tank_cm']*CONV['main'], last['Receiving_Tank_cm']*CONV['rec'], last['Daily_Tank_cm']*CONV['daily'], last['Boiler_Tank_cm']*CONV['boil']
        
        m[0].metric("Emergency", f"{v_m:,.0f} L")
        m[1].metric("Receiving", f"{v_r:,.0f} L")
        m[2].metric("Daily", f"{v_d:,.0f} L")
        m[3].metric("Boiler", f"{v_b:,.0f} L")
        st.info(f"⚡ **Total Stock:** {v_m+v_r+v_d+v_b:,.0f} Liters")

        # --- حساب المصروف الحقيقي (تجاهل الزيادة الناتجة عن النقل) ---
        if len(df) >= 2:
            prev = df.iloc[-2]
            st.divider()
            st.subheader("📉 Actual Consumption (Last Update)")
            c = st.columns(4)
            
            # الدالة الذكية: تحسب الفرق فقط إذا كان نقصاً، وإذا زاد الخزان (تعبئة) تعتبر الصرف 0
            def get_usage(curr, pre, factor):
                diff = pre - curr
                return diff * factor if diff > 0 else 0.0

            u_m = get_usage(last['Main_Tank_cm'], prev['Main_Tank_cm'], CONV['main'])
            u_r = get_usage(last['Receiving_Tank_cm'], prev['Receiving_Tank_cm'], CONV['rec'])
            u_d = get_usage(last['Daily_Tank_cm'], prev['Daily_Tank_cm'], CONV['daily'])
            u_b = get_usage(last['Boiler_Tank_cm'], prev['Boiler_Tank_cm'], CONV['boil'])
            
            c[0].write(f"**Emerg. Used:** {u_m:,.1f} L")
            c[1].write(f"**Rec. Used:** {u_r:,.1f} L") # هذا سيظهر الـ 51 سم التي سحبتها اليوم كـ "استهلاك" من هذا الخزان
            c[2].write(f"**Gen. Burned:** {u_d:,.1f} L") # هذا سيظهر 0 إذا كنت قد ملأت الخزان للتو
            c[3].write(f"**Boiler Burned:** {u_b:,.1f} L")

        # --- الرسم البياني الرباعي ---
        st.divider()
        st.subheader("📈 Historical Tank Trends")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Main_Tank_cm']*CONV['main'], name='Emergency', line=dict(color='red')))
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Receiving_Tank_cm']*CONV['rec'], name='Receiving', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Daily_Tank_cm']*CONV['daily'], name='Daily', line=dict(color='green')))
        fig.add_trace(go.Scatter(x=df['Timestamp'], y=df['Boiler_Tank_cm']*CONV['boil'], name='Boiler', line=dict(color='orange')))
        fig.update_layout(hovermode="x unified", legend_orientation="h")
        st.plotly_chart(fig, use_container_width=True)

        # --- التصدير ---
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Full History (CSV)", csv, "fuel_report.csv", "text/csv")
