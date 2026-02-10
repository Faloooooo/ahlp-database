import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import io

# --- 1. إعدادات الصفحة والروابط ---
st.set_page_config(page_title="Ramada Plaza Energy System", layout="wide", page_icon="🏨")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'water': '423939923', 'gas': '578874363', 'electricity': '1588872380', 'generators': '1679289485'}
CONV_FUEL = {'main': 107.22, 'rec': 37.6572, 'daily': 31.26, 'boil': 37.6572}

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
mode = st.sidebar.radio("Main Menu:", ["📊 Operations Reports", "✍️ Daily Data Entry"])

# ==========================================
# SECTION 1: DATA ENTRY (تثبيت الترتيب)
# ==========================================
if mode == "✍️ Daily Data Entry":
    st.header("✍️ Operational Data Recording")
    category = st.selectbox("Utility Category:", ["Diesel (Fuel)", "Water", "Gas (Propane)", "EDL (Electricity)", "Generators"])
    
    with st.form("main_entry_form", clear_on_submit=True):
        if category == "Diesel (Fuel)":
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

        elif category == "Water":
            st.subheader("💧 Water Data Entry")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🚚 Truck Water")
                tc = st.number_input("Extra Truck Count", step=1)
                ts = st.number_input("Truck Size M3", value=20.0)
                tp = st.number_input("Truck Cost USD")
            with col2:
                st.markdown("### 🏛️ City Water")
                cw = st.number_input("City Water Reading (m³)", step=0.1)
                cb = st.number_input("City Bill USD")
                of = st.number_input("Other Water Fees")
            vals, s_name = [cw, tc, ts, tp, cb, of], "Water_Data"
        
        # الأقسام الأخرى بنفس الترتيب
        elif category == "Generators":
            v = []
            for i in range(1, 4):
                col1, col2 = st.columns(2); v.extend([col1.number_input(f"kWh G{i}", key=f"k{i}"), col2.number_input(f"SMU G{i}", key=f"s{i}")])
            vals, s_name = v, "Generators_kwh"
        
        elif category == "Gas (Propane)":
            vals, s_name = [st.number_input("Tank %"), st.number_input("Bought Ltr"), 0, 0], "Gas_Data"

        elif category == "EDL (Electricity)":
            vals, s_name = [st.number_input("Night"), st.number_input("Peak"), st.number_input("Day"), st.number_input("Total Bill")], "Electricity_Accrual"

        if st.form_submit_button("🚀 Submit Data"):
            if send_to_google(s_name, vals): st.success("✅ Data Sent Successfully!")
            else: st.error("❌ Link Error")

# ==========================================
# SECTION 2: REPORTS (إعادة تفعيل المازوت بالكامل)
# ==========================================
else:
    report_type = st.sidebar.selectbox("Select Report:", ["Diesel Report (Fixed)", "Water Analysis (New)"])
    col_d1, col_d2 = st.columns(2)
    sd = col_d1.date_input("From Date", datetime.now() - timedelta(days=7))
    ed = col_d2.date_input("To Date", datetime.now())

    if report_type == "Diesel Report (Fixed)":
        df = load_data('fuel')
        if not df.empty:
            last = df.iloc[-1]
            st.subheader("📍 Current Fuel Inventory (Liters)")
            m = st.columns(4)
            # استخدام أسماء الأعمدة الفعلية لضمان الدقة
            vals = {'Emergency': last.iloc[1]*CONV_FUEL['main'], 'Receiving': last.iloc[2]*CONV_FUEL['rec'], 
                    'Daily': last.iloc[3]*CONV_FUEL['daily'], 'Boiler': last.iloc[4]*CONV_FUEL['boil']}
            
            for i, (name, val) in enumerate(vals.items()):
                m[i].metric(name, f"{val:,.0f} L")

            # --- استعادة حساب المصروف الحقيقي بين آخر قرائتين ---
            if len(df) >= 2:
                prev = df.iloc[-2]
                st.divider()
                st.subheader("📉 Consumption in Last Update")
                c = st.columns(4)
                # دالة حساب الفرق (فقط إذا كان نقصاً)
                def get_diff(c, p, f):
                    d = p - c
                    return d * f if d > 0 else 0.0
                
                c[0].write(f"**Emerg. Used:** {get_diff(last.iloc[1], prev.iloc[1], CONV_FUEL['main']):,.1f} L")
                c[1].write(f"**Rec. Used:** {get_diff(last.iloc[2], prev.iloc[2], CONV_FUEL['rec']):,.1f} L")
                c[2].write(f"**Daily Burned:** {get_diff(last.iloc[3], prev.iloc[3], CONV_FUEL['daily']):,.1f} L")
                c[3].write(f"**Boiler Burned:** {get_diff(last.iloc[4], prev.iloc[4], CONV_FUEL['boil']):,.1f} L")

            # --- إعادة الخطوط الأربعة للرسم البياني ---
            st.divider()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Timestamp'], y=df.iloc[:,1]*CONV_FUEL['main'], name='Emergency', line=dict(color='red')))
            fig.add_trace(go.Scatter(x=df['Timestamp'], y=df.iloc[:,2]*CONV_FUEL['rec'], name='Receiving', line=dict(color='blue')))
            fig.add_trace(go.Scatter(x=df['Timestamp'], y=df.iloc[:,3]*CONV_FUEL['daily'], name='Daily', line=dict(color='green')))
            fig.add_trace(go.Scatter(x=df['Timestamp'], y=df.iloc[:,4]*CONV_FUEL['boil'], name='Boiler', line=dict(color='orange')))
            fig.update_layout(title="Historical Inventory (4 Tanks)", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

    elif report_type == "Water Analysis (New)":
        st.header("💧 Water Analysis")
        dfw = load_data('water')
        if not dfw.empty:
            mask = (dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)
            dff = dfw.loc[mask]
            if not dff.empty:
                # حسابات مياه الدولة والصهاريج
                c_start, c_end = dff.iloc[0, 1], dff.iloc[-1, 1]
                t_m3 = dff.iloc[:, 2].sum() * dff.iloc[0, 3] if not pd.isna(dff.iloc[0, 3]) else 0
                st.subheader(f"Summary: {sd} to {ed}")
                m1, m2, m3 = st.columns(3)
                m1.metric("City Water", f"{max(0, c_end - c_start):,.1f} m³")
                m2.metric("Trucks Water", f"{t_m3:,.1f} m³")
                m3.metric("Total Cost", f"${(dff.iloc[:, 4].sum() + dff.iloc[:, 5].sum() + dff.iloc[:, 6].sum()):,.2f}")
