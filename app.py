import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import io

# --- 1. الإعدادات والروابط ---
st.set_page_config(page_title="Ramada Plaza Energy System", layout="wide", page_icon="🏨")

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
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == "AHLP2026":
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 3. القائمة الجانبية ---
mode = st.sidebar.radio("Main Menu:", ["📊 Performance Reports", "✍️ Daily Data Entry"])

# ==========================================
# ✍️ قسم إدخال البيانات (Data Entry)
# ==========================================
if mode == "✍️ Daily Data Entry":
    st.header("✍️ Daily Operational Entry")
    category = st.selectbox("Category:", ["Diesel (Fuel)", "Water", "Gas (Propane)", "EDL (Electricity)", "Generators"])
    
    with st.form("entry_form", clear_on_submit=True):
        if category == "Diesel (Fuel)":
            c1, c2 = st.columns(2)
            m = c1.number_input("Emergency Tank (cm)", min_value=0.0)
            r = c2.number_input("Receiving Tank (cm)", min_value=0.0)
            d = c1.number_input("Daily Tank (cm)", min_value=0.0)
            b = c2.number_input("Boiler Tank (cm)", min_value=0.0)
            bl = st.number_input("Bought Liters Today", min_value=0.0)
            bp = st.number_input("Total Purchase Price (USD)", min_value=0.0)
            vals, s_name = [m, r, d, b, bl, bp], "Fuel_Data"

        elif category == "Water":
            col1, col2 = st.columns(2)
            with col1:
                tc = st.number_input("Truck Count", step=1)
                ts = st.number_input("Truck Size M3", value=20.0)
                tp = st.number_input("Truck Cost USD")
            with col2:
                cw = st.number_input("City Meter Reading m³")
                cb = st.number_input("City Bill USD")
                of = st.number_input("Other Fees USD")
            vals, s_name = [cw, tc, ts, tp, cb, of], "Water_Data"
        
        # تكرار لبقية التصنيفات بشكل مبسط لضمان عمل الكود
        else:
            st.info("Coming soon...")
            vals, s_name = [], ""

        if st.form_submit_button("🚀 Submit to Database"):
            if s_name and send_to_google(s_name, vals):
                st.success(f"✅ {category} data successfully uploaded!")
            else:
                st.error("❌ Submission Failed. Check Connection.")

# ==========================================
# 📊 قسم التقارير (Reports)
# ==========================================
else:
    report = st.sidebar.selectbox("Choose Report:", ["Diesel Report", "Water Analysis"])
    c_d1, c_d2 = st.columns(2)
    sd, ed = c_d1.date_input("From Date", datetime.now()-timedelta(7)), c_d2.date_input("To Date", datetime.now())

    if report == "Diesel Report":
        df = load_data('fuel')
        if not df.empty:
            # فلترة حسب التاريخ
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)]
            
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                
                # 1. المخزون الحالي (Current Stock)
                st.subheader("📍 Current Stock (Liters)")
                m = st.columns(4)
                m[0].metric("Emergency", f"{last.iloc[1]*CONV['main']:,.0f} L")
                m[1].metric("Receiving", f"{last.iloc[2]*CONV['rec']:,.0f} L")
                m[2].metric("Daily", f"{last.iloc[3]*CONV['daily']:,.0f} L")
                m[3].metric("Boiler", f"{last.iloc[4]*CONV['boil']:,.0f} L")

                # 2. استهلاك آخر تحديث (Consumption Last Update)
                if len(df) >= 2:
                    st.divider()
                    st.subheader("⏱️ Consumption - Last Update vs Previous")
                    prev = df.iloc[-2]
                    c = st.columns(4)
                    
                    def get_usage(curr, pre, factor):
                        diff = pre - curr
                        return diff * factor if diff > 0 else 0.0

                    # تصحيح الـ f-string الذي ظهر في الصورة 5
                    c[0].metric("Emergency spent", f"{get_usage(last.iloc[1], prev.iloc[1], CONV['main']):,.1f} L")
                    c[1].metric("Receiving spent", f"{get_usage(last.iloc[2], prev.iloc[2], CONV['rec']:,.1f} L")
                    c[2].metric("Daily spent", f"{get_usage(last.iloc[3], prev.iloc[3], CONV['daily']):,.1f} L")
                    c[3].metric("Boiler spent", f"{get_usage(last.iloc[4], prev.iloc[4], CONV['boil']):,.1f} L")

                # 3. الرسم البياني (تم تصحيح KeyError من الصورة 1)
                st.divider()
                st.subheader("📈 Historical Trends")
                fig = go.Figure()
                colors = ['red', 'blue', 'green', 'orange']
                labels = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                factors = [CONV['main'], CONV['rec'], CONV['daily'], CONV['boil']]
                
                for i in range(4):
                    fig.add_trace(go.Scatter(
                        x=df_filt['Timestamp'], 
                        y=df_filt.iloc[:, i+1] * factors[i], 
                        name=labels[i], 
                        line=dict(color=colors[i], width=2)
                    ))
                fig.update_layout(hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

    elif report == "Water Analysis":
        dfw = load_data('water')
        if not dfw.empty:
            st.header("💧 Water Analysis Report")
            mask = (dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)
            dff = dfw.loc[mask]
            if not dff.empty:
                # حسابات دقيقة
                city_m3 = max(0, dff.iloc[-1, 1] - dff.iloc[0, 1])
                truck_count = dff.iloc[:, 2].sum()
                truck_size = dff.iloc[-1, 3] if not pd.isna(dff.iloc[-1, 3]) else 20
                truck_m3 = truck_count * truck_size
                
                c
