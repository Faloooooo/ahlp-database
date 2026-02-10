import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات الأساسية ---
st.set_page_config(page_title="Ramada Management System", layout="wide")

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

# --- 2. الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == "AHLP2026":
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 3. القائمة ---
mode = st.sidebar.radio("Main Menu:", ["📊 Performance Reports", "✍️ Data Entry"])

if mode == "✍️ Data Entry":
    st.header("✍️ Daily Data Entry")
    cat = st.selectbox("Category:", ["Diesel (Fuel)", "Water"])
    with st.form("main_form", clear_on_submit=True):
        if cat == "Diesel (Fuel)":
            c1, c2 = st.columns(2)
            m = c1.number_input("Emergency (cm)", min_value=0.0, format="%.2f")
            r = c2.number_input("Receiving (cm)", min_value=0.0, format="%.2f")
            d = c1.number_input("Daily (cm)", min_value=0.0, format="%.2f")
            b = c2.number_input("Boiler (cm)", min_value=0.0, format="%.2f")
            bl = st.number_input("Bought Liters Today", min_value=0.0)
            bp = st.number_input("Total Purchase Price (USD)", min_value=0.0)
            vals, s_name = [m, r, d, b, bl, bp], "Fuel_Data"
        else:
            col1, col2 = st.columns(2)
            tc = col1.number_input("Truck Count", step=1)
            ts = col1.number_input("Truck Size M3", value=20.0)
            tp = col1.number_input("Truck Cost USD")
            cw = col2.number_input("City Meter Reading m³")
            cb = col2.number_input("City Bill USD")
            of = col2.number_input("Other Fees USD")
            vals, s_name = [cw, tc, ts, tp, cb, of], "Water_Data"
        
        if st.form_submit_button("Submit Data"):
            if send_to_google(s_name, vals): st.success("✅ Data Sent Successfully!")
            else: st.error("❌ Link Error")

else:
    report = st.sidebar.selectbox("Report Type:", ["Diesel Analysis", "Water Analysis"])
    c1, c2 = st.columns(2)
    sd, ed = c1.date_input("From", datetime.now()-timedelta(7)), c2.date_input("To", datetime.now())

    if report == "Diesel Analysis":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)]
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                
                # --- القسم المطلوب: كم صرفت من آخر بيانات ---
                if len(df) >= 2:
                    st.subheader("📉 Consumption (Liters) - Last Update")
                    prev = df.iloc[-2]
                    cols = st.columns(4)
                    
                    def get_usage(curr, pre, factor):
                        diff = float(pre) - float(curr)
                        return diff * factor if diff > 0 else 0.0

                    cols[0].metric("Emergency spent", f"{get_usage(last.iloc[1], prev.iloc[1], CONV['main']):,.1f} L")
                    cols[1].metric("Receiving spent", f"{get_usage(last.iloc[2], prev.iloc[2], CONV['rec']):,.1f} L")
                    cols[2].metric("Daily spent", f"{get_usage(last.iloc[3], prev.iloc[3], CONV['daily']):,.1f} L")
                    cols[3].metric("Boiler spent", f"{get_usage(last.iloc[4], prev.iloc[4], CONV['boil']):,.1f} L")

                # --- المخزون الحالي ---
                st.divider()
                st.subheader("📍 Current Inventory")
                m = st.columns(4)
                m[0].metric("Emergency", f"{last.iloc[1]*CONV['main']:,.0f} L")
                m[1].metric("Receiving", f"{last.iloc[2]*CONV['rec']:,.0f} L")
                m[2].metric("Daily", f"{last.iloc[3]*CONV['daily']:,.0f} L")
                m[3].metric("Boiler", f"{last.iloc[4]*CONV['boil']:,.0f} L")

                # --- الرسم البياني الموحد (إصلاح أخطاء الأقواس) ---
                st.divider()
                fig = go.Figure()
                clrs = ['red', 'blue', 'green', 'orange']
                lbls = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                fcts = [CONV['main'], CONV['rec'], CONV['daily'], CONV['boil']]
                
                for i in range(4):
                    fig.add_trace(go.Scatter(
                        x=df_filt['Timestamp'], 
                        y=df_filt.iloc[:, i+1]*fcts[i], 
                        name=lbls[i], 
                        line=dict(color=clrs[i])
                    ))
                fig.update_layout(title="Historical Inventory Trends", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

    elif report == "Water Analysis":
        dfw = load_data('water')
        if not dfw.empty:
            dff = dfw[(dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)]
            if not dff.empty:
                st.header("💧 Water Analysis Report")
                city_m3 = max(0, dff.iloc[-1, 1] - dff.iloc[0, 1])
                truck_count = dff.iloc[:, 2].sum()
                truck_size = dff.iloc[-1, 3] if not pd.isna(dff.iloc[-1, 3]) else 20
                truck_m3 = truck_count * truck_size
                
                res = st.columns(3)
                res[0].metric("City Water m³", f"{city_m3:,.1f}")
                res[1].metric("Truck Water m³", f"{truck_m3:,.1f}")
                res[2].metric("Total Water m³", f"{(city_m3 + truck_m3):,.1f}")
                
                # تحميل البيانات (CSV لضمان التوافق)
                csv = dff.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Report (CSV)", csv, "water_data.csv", "text/csv")
