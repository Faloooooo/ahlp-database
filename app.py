import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import io

# Page Configuration
st.set_page_config(page_title="AHLP Management System", layout="wide", page_icon="🏨")

# Connections & Constants
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxITTacKEMsGtc4V0aJOlJPnmcXEZrnyfM95tVOUWzcL1U7T8DYMWfEyEvyIwjyhGmW/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'gas': '578874363', 'water': '423939923', 'electricity': '1588872380', 'generators': '1679289485'}
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
        response = requests.post(f"{SCRIPT_URL}?sheet={sheet_name}", data=json.dumps({"values": values}))
        return response.status_code == 200
    except: return False

# --- Authentication ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 AHLP System Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- Navigation ---
mode = st.sidebar.radio("Navigation:", ["📊 Performance Reports", "✍️ Data Entry"])

if mode == "✍️ Data Entry":
    st.header("✍️ Daily Data Input")
    category = st.selectbox("Category:", ["Diesel (Fuel)", "Water", "Gas (Propane)", "Generators", "EDL (Electricity)"])
    # [Internal Note: Keep existing stable data entry form logic here]
    st.info("Form is active. Enter data and click submit.")

else: # --- Performance Reports (The Intelligent Part) ---
    st.header("📊 Performance & Analytics Dashboard")
    report_type = st.sidebar.selectbox("Report View:", ["Fuel & Energy Trends", "Water & Gas Detailed", "Monthly Summary Table"])
    
    col_d1, col_d2 = st.columns(2)
    start_d = col_d1.date_input("From Date", datetime.now().replace(day=1))
    end_d = col_d2.date_input("To Date", datetime.now())

    # --- FUEL SECTION (Detailed) ---
    if report_type == "Fuel & Energy Trends":
        df_f = load_data('fuel')
        if not df_f.empty:
            for c in ['Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm']:
                if c not in df_f.columns: df_f[c] = 0.0
            
            mask = (df_f['Timestamp'].dt.date >= start_d) & (df_f['Timestamp'].dt.date <= end_d)
            f_filtered = df_f.loc[mask]
            
            if not f_filtered.empty:
                last = f_filtered.iloc[-1]
                l_main, l_rec = last['Main_Tank_cm']*CONV['main'], last['Receiving_Tank_cm']*CONV['rec']
                l_daily, l_boil = last['Daily_Tank_cm']*CONV['daily'], last['Boiler_Tank_cm']*CONV['boil']
                
                st.subheader("📍 Current Fuel Inventory (Liters)")
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Emergency", f"{l_main:,.0f} L")
                m2.metric("Receiving", f"{l_rec:,.0f} L")
                m3.metric("Daily (Gen)", f"{l_daily:,.0f} L")
                m4.metric("Boiler", f"{l_boil:,.0f} L")
                m5.metric("TOTAL STOCK", f"{l_main+l_rec+l_daily+l_boil:,.0f} L")

                # Consumption Analysis Chart
                st.markdown("---")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=f_filtered['Timestamp'], y=f_filtered['Main_Tank_cm']*CONV['main'], name='Emergency'))
                fig.add_trace(go.Scatter(x=f_filtered['Timestamp'], y=f_filtered['Boiler_Tank_cm']*CONV['boil'], name='Boiler (Heating)'))
                fig.update_layout(title="Tank Inventory Trends (Liters)", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

    # --- WATER & GAS SECTION (Detailed) ---
    elif report_type == "Water & Gas Detailed":
        st.subheader("💧 Water & Gas Consumption Tracking")
        df_w = load_data('water')
        if not df_w.empty:
            w_mask = (df_w['Timestamp'].dt.date >= start_d) & (df_w['Timestamp'].dt.date <= end_d)
            w_filtered = df_w.loc[w_mask]
            
            if not w_filtered.empty:
                # Calculate Daily Consumption (Difference between readings)
                w_filtered = w_filtered.sort_values('Timestamp')
                w_filtered['Daily_Usage_m3'] = w_filtered['City_Water_Reading'].diff().fillna(0)
                
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**City Water Meter Trend (m³)**")
                    st.line_chart(w_filtered.set_index('Timestamp')['City_Water_Reading'])
                with c2:
                    st.write("**Daily Consumption Rate (m³)**")
                    st.bar_chart(w_filtered.set_index('Timestamp')['Daily_Usage_m3'])

                # Export Button for Water
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    w_filtered.to_excel(writer, sheet_name='Water_Report', index=False)
                st.download_button("📥 Export Water Data to Excel", buffer.getvalue(), "Water_Report.xlsx", "application/vnd.ms-excel")

    # --- MONTHLY SUMMARY TABLE ---
    elif report_type == "Monthly Summary Table":
        st.subheader("📋 Executive Utility Summary")
        # Logic to compile costs from all sheets...
        st.info("This section aggregates total monthly costs for management review.")
