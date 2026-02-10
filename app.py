import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import io

# --- 1. إعدادات الصفحة والروابط الثابتة ---
st.set_page_config(page_title="Ramada Plaza Energy System", layout="wide", page_icon="🏨")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'water': '423939923', 'gas': '578874363', 'electricity': '1588872380', 'generators': '1679289485'}
CONV_FUEL = {'main': 107.22, 'rec': 37.6572, 'daily': 31.26, 'boil': 37.6572}

# --- 2. الدوال التقنية ---
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

# --- 3. تسجيل الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 4. القائمة الجانبية ---
mode = st.sidebar.radio("Main Menu:", ["📊 Operations Reports", "✍️ Daily Data Entry"])

# ==========================================
# قسم إدخال البيانات (Data Entry)
# ==========================================
if mode == "✍️ Daily Data Entry":
    st.header("✍️ Operational Data Recording")
    category = st.selectbox("Utility Category:", ["Water", "Diesel (Fuel)", "Gas (Propane)", "EDL (Electricity)", "Generators"])
    
    with st.form("main_entry_form", clear_on_submit=True):
        if category == "Water":
            st.subheader("💧 Water Data Entry")
            # تنظيم الخانات حسب طلبك (الصهاريج وحدها والدولة وحدها)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🚚 Truck Water (الصهاريج)")
                tc = st.number_input("Extra Truck Count", step=1)
                ts = st.number_input("Truck Size M3", value=20.0)
                tp = st.number_input("Truck Cost USD")
            with col2:
                st.markdown("### 🏛️ City Water (مياه الدولة)")
                cw = st.number_input("City Water Reading (m³)", step=0.1)
                cb = st.number_input("City Bill USD")
                of = st.number_input("Other Water Fees")
            
            # ترتيب الترحيل: 1:Reading, 2:Count, 3:Size, 4:Cost, 5:Bill, 6:Fees
            vals, s_name = [cw, tc, ts, tp, cb, of], "Water_Data"

        elif category == "Diesel (Fuel)":
            st.subheader("⛽ Fuel Tank Levels (cm)")
            c1, c2 = st.columns(2)
            vals, s_name = [c1.number_input("Emergency Tank"), c2.number_input("Receiving Tank"), 
                            c1.number_input("Daily Tank"), c2.number_input("Boiler Tank"),
                            st.number_input("Bought Liters Today"), st.number_input("Total Purchase Price (USD)")], "Fuel_Data"
        
        # (بقية الأقسام المولدات والغاز تعمل بنفس المنطق السابق)
        elif category == "Generators":
            v = []
            for i in range(1, 4):
                col1, col2 = st.columns(2)
                v.extend([col1.number_input(f"kWh G{i}", key=f"k{i}"), col2.number_input(f"SMU G{i}", key=f"s{i}")])
            vals, s_name = v, "Generators_kwh"
        
        elif category == "Gas (Propane)":
            vals, s_name = [st.number_input("Tank %"), st.number_input("Bought Ltr"), 0, 0], "Gas_Data"

        elif category == "EDL (Electricity)":
            vals, s_name = [st.number_input("Night"), st.number_input("Peak"), st.number_input("Day"), st.number_input("Total Bill")], "Electricity_Accrual"

        if st.form_submit_button("🚀 Submit Data"):
            if send_to_google(s_name, vals): st.success("✅ Data Sent Successfully!")
            else: st.error("❌ Link Error")

# ==========================================
# قسم التقارير (Reports & Analytics)
# ==========================================
else:
    report_type = st.sidebar.selectbox("Select Report:", ["Diesel Report (Fixed)", "Water Analysis (New)"])
    
    # فلتر التاريخ المشترك
    col_d1, col_d2 = st.columns(2)
    sd = col_d1.date_input("From Date", datetime.now() - timedelta(days=7))
    ed = col_d2.date_input("To Date", datetime.now())

    # --- تقرير المازوت (مثبت) ---
    if report_type == "Diesel Report (Fixed)":
        df = load_data('fuel')
        if not df.empty:
            last = df.iloc[-1]
            st.subheader("📍 Current Fuel Inventory")
            m = st.columns(4)
            m[0].metric("Emergency", f"{last.iloc[1]*CONV_FUEL['main']:,.0f} L")
            m[1].metric("Receiving", f"{last.iloc[2]*CONV_FUEL['rec']:,.0f} L")
            m[2].metric("Daily", f"{last.iloc[3]*CONV_FUEL['daily']:,.0f} L")
            m[3].metric("Boiler", f"{last.iloc[4]*CONV_FUEL['boil']:,.0f} L")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Timestamp'], y=df.iloc[:,1]*CONV_FUEL['main'], name='Emergency'))
            fig.add_trace(go.Scatter(x=df['Timestamp'], y=df.iloc[:,3]*CONV_FUEL['daily'], name='Daily'))
            st.plotly_chart(fig, use_container_width=True)

    # --- تقرير المياه (الجديد بالكامل) ---
    elif report_type == "Water Analysis (New)":
        st.header("💧 Water Consumption & Cost Analysis")
        dfw = load_data('water')
        
        if not dfw.empty:
            # تصفية حسب التاريخ
            mask = (dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)
            df_filtered = dfw.loc[mask]
            
            if not df_filtered.empty:
                # 1. حسابات مياه الدولة (الفرق بين القراءات)
                city_start = df_filtered.iloc[0, 1] # أول قراءة في الفترة
                city_end = df_filtered.iloc[-1, 1]   # آخر قراءة في الفترة
                total_city_m3 = max(0, city_end - city_start)
                
                # 2. حسابات الصهاريج
                total_trucks = df_filtered.iloc[:, 2].sum() # مجموع عدد الصهاريج
                truck_size = df_filtered.iloc[0, 3] if not pd.isna(df_filtered.iloc[0, 3]) else 0
                total_truck_m3 = total_trucks * truck_size
                total_truck_cost = df_filtered.iloc[:, 4].sum() # مجموع التكلفة
                
                # 3. المصاريف الأخرى ومياه الدولة
                total_city_bills = df_filtered.iloc[:, 5].sum()
                total_other_fees = df_filtered.iloc[:, 6].sum()
                
                # العرض بالأرقام (Metrics)
                st.subheader(f"📊 Summary for Period: {sd} to {ed}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("City Water Cons.", f"{total_city_m3:,.1f} m³")
                m2.metric("Trucks Water Cons.", f"{total_truck_m3:,.1f} m³")
                m3.metric("Total Water Cons.", f"{(total_city_m3 + total_truck_m3):,.1f} m³")
                m4.metric("Total Water Cost", f"${(total_truck_cost + total_city_bills + total_other_fees):,.2f}")
                
                st.divider()
                st.subheader("🚚 Truck Details")
                c1, c2 = st.columns(2)
                c1.info(f"Total Trucks Purchased: **{total_trucks:,.0f} Trucks**")
                c2.warning(f"Average Truck Cost: **${(total_truck_cost/total_trucks if total_trucks > 0 else 0):,.2f}**")
                
                # رسم بياني لمقارنة مياه الدولة مقابل الصهاريج
                fig_water = go.Figure(data=[
                    go.Bar(name='City Water', x=['Total Volume m³'], y=[total_city_m3]),
                    go.Bar(name='Truck Water', x=['Total Volume m³'], y=[total_truck_m3])
                ])
                fig_water.update_layout(barmode='group', title="City vs Truck Water Volume")
                st.plotly_chart(fig_water, use_container_width=True)

                # زر التصدير
                csv = df_filtered.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export Water Report (CSV)", csv, "water_report.csv", "text/csv")
