import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import io

# --- 1. إعدادات الصفحة والروابط الثابتة (لا يتم تغييرها) ---
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
# SECTION: DATA ENTRY (مثبتة بالكامل)
# ==========================================
if mode == "✍️ Daily Data Entry":
    st.header("✍️ Operational Data Recording")
    category = st.selectbox("Utility Category:", ["Diesel (Fuel)", "Water", "Gas (Propane)", "EDL (Electricity)", "Generators"])
    
    with st.form("main_entry_form", clear_on_submit=True):
        if category == "Diesel (Fuel)":
            st.subheader("⛽ Fuel Tank Levels (cm)")
            c1, c2 = st.columns(2)
            m, r, d, b = c1.number_input("Emergency Tank"), c2.number_input("Receiving Tank"), c1.number_input("Daily Tank"), c2.number_input("Boiler Tank")
            bl, bp = st.number_input("Bought Liters Today"), st.number_input("Total Purchase Price (USD)")
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
# SECTION: REPORTS (تعديل تقرير المياه فقط)
# ==========================================
else:
    report_type = st.sidebar.selectbox("Select Report:", ["Diesel Report (Fixed)", "Water Report (Enhanced)"])
    col_d1, col_d2 = st.columns(2)
    sd = col_d1.date_input("From Date", datetime.now() - timedelta(days=7))
    ed = col_d2.date_input("To Date", datetime.now())

    if report_type == "Diesel Report (Fixed)":
        # (قسم تقرير المازوت الثابت كما هو تماماً)
        df = load_data('fuel')
        if not df.empty:
            last = df.iloc[-1]
            st.subheader("📍 Current Fuel Inventory (Liters)")
            m = st.columns(4)
            m[0].metric("Emergency", f"{last.iloc[1]*CONV_FUEL['main']:,.0f} L")
            m[1].metric("Receiving", f"{last.iloc[2]*CONV_FUEL['rec']:,.0f} L")
            m[2].metric("Daily", f"{last.iloc[3]*CONV_FUEL['daily']:,.0f} L")
            m[3].metric("Boiler", f"{last.iloc[4]*CONV_FUEL['boil']:,.0f} L")
            
            fig = go.Figure()
            for i, name, color in zip([1,2,3,4],['Emergency','Receiving','Daily','Boiler'],['red','blue','green','orange']):
                fig.add_trace(go.Scatter(x=df['Timestamp'], y=df.iloc[:,i]*CONV_FUEL[name[:3].lower() if name != 'Emergency' else 'main'], name=name, line=dict(color=color)))
            st.plotly_chart(fig, use_container_width=True)

    elif report_type == "Water Report (Enhanced)":
        st.header("💧 Water Performance Report")
        dfw = load_data('water')
        if not dfw.empty:
            mask = (dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)
            dff = dfw.loc[mask]
            
            if not dff.empty:
                # 1. حسابات مياه الدولة
                city_m3 = max(0, dff.iloc[-1, 1] - dff.iloc[0, 1])
                city_cost = dff.iloc[:, 5].sum() + dff.iloc[:, 6].sum() # City Bill + Other Fees
                
                # 2. حسابات الصهاريج
                truck_count = dff.iloc[:, 2].sum()
                truck_m3 = truck_count * (dff.iloc[0, 3] if not pd.isna(dff.iloc[0, 3]) else 0)
                truck_cost = dff.iloc[:, 4].sum()
                
                # 3. الإجماليات
                total_m3 = city_m3 + truck_m3
                total_cost = city_cost + truck_cost
                
                # --- العرض حسب طلبك ---
                st.subheader("📈 Consumption Summary")
                c1, c2, c3 = st.columns(3)
                c1.metric("City Water m³", f"{city_m3:,.1f}")
                c2.metric("Trucks Water m³", f"{truck_m3:,.1f}")
                c3.metric("TOTAL m³", f"{total_m3:,.1f}", delta_color="normal")
                
                st.subheader("💰 Cost Summary (USD)")
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("City Cost", f"${city_cost:,.2f}")
                k2.metric("Trucks Count", f"{truck_count:,.0f}")
                k3.metric("Trucks Total Cost", f"${truck_cost:,.2f}")
                k4.metric("TOTAL COST", f"${total_cost:,.2f}")
                
                # رسم بياني توضيحي
                fig_w = go.Figure(data=[
                    go.Bar(name='City Water', x=['Volume (m³)'], y=[city_m3], marker_color='royalblue'),
                    go.Bar(name='Trucks Water', x=['Volume (m³)'], y=[truck_m3], marker_color='lightblue')
                ])
                fig_w.update_layout(barmode='group', title="City vs Trucks Usage")
                st.plotly_chart(fig_w, use_container_width=True)

                # التصدير
                csv = dff.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export Period Data (CSV)", csv, "water_report.csv", "text/csv")
