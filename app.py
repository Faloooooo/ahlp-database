import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="AHLP Management System", layout="wide", page_icon="🏨")

# الروابط
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxITTacKEMsGtc4V0aJOlJPnmcXEZrnyfM95tVOUWzcL1U7T8DYMWfEyEvyIwjyhGmW/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {
    'fuel': '1077908569',
    'gas': '578874363',
    'water': '423939923',
    'electricity': '1588872380',
    'generators': '1679289485'
}

def send_to_google(sheet_name, values):
    try:
        response = requests.post(f"{SCRIPT_URL}?sheet={sheet_name}", data=json.dumps({"values": values}))
        return response.status_code == 200
    except: return False

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except: return pd.DataFrame()

# --- حماية الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 دخول نظام AHLP")
    pwd = st.text_input("أدخل كلمة المرور", type="password")
    if st.button("دخول"):
        if pwd == "AHLP2026":
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("كلمة المرور خاطئة")
    st.stop()

# --- القائمة الرئيسية ---
st.sidebar.title(f"مرحباً بك، {datetime.now().strftime('%Y-%m-%d')}")
mode = st.sidebar.radio("اختر المهمة:", ["📊 لوحة التحكم والتقارير", "✍️ إدخال بيانات جديدة"])

if mode == "✍️ إدخال بيانات جديدة":
    category = st.selectbox("القسم:", ["المازوت", "الغاز", "المياه", "المولدات (1-5)", "كهرباء الدولة"])
    
    with st.form("main_form", clear_on_submit=True):
        if category == "المازوت":
            vals = [st.number_input("الطوارئ (cm)"), st.number_input("الاستقبال (cm)"), st.number_input("المولدات (cm)"), st.number_input("البويلر (cm)"), 0, st.number_input("السعر USD")]
            s_name = "Fuel_Data"
        
        elif category == "الغاز":
            vals = [st.number_input("نسبة تخزين الغاز %")]
            s_name = "Gas_Data"

        elif category == "المياه":
            vals = [st.number_input("قراءة عداد المياه m³")]
            s_name = "Water_Data" 

        elif category == "المولدات (1-5)":
            st.info("أدخل قراءة العداد (kWh) وساعات العمل (SMU) لكل مولد")
            c1, c2 = st.columns(2)
            v = []
            for i in range(1, 6):
                v.append(c1.number_input(f"المولد {i} - kWh", key=f"k{i}"))
                v.append(c2.number_input(f"المولد {i} - SMU", key=f"s{i}"))
            vals = v
            s_name = "Generators_kwh"
            
        elif category == "كهرباء الدولة":
            vals = [st.number_input("عداد كهرباء الدولة الرئيسي (kWh)")]
            s_name = "Electricity_Accrual"

        if st.form_submit_button("إرسال البيانات"):
            if send_to_google(s_name, vals): st.success("✅ تم الحفظ بنجاح")
            else: st.error("❌ فشل الاتصال بالسيرفر")

else: # لوحة التحكم والتقارير
    st.header("📊 مراجعة القراءات والتقارير")
    tab_fuel, tab_gen, tab_others = st.tabs(["⛽ مخزون الوقود", "⚡ المولدات", "💧 الغاز والمياه والكهرباء"])
    
    with tab_fuel:
        df_f = load_data('fuel')
        if not df_f.empty:
            st.metric("آخر قراءة للطوارئ", f"{df_f.iloc[-1]['Main_Tank_cm'] * 107:,.0f} L")
            st.line_chart(df_f.set_index('Timestamp')['Main_Tank_cm'])

    with tab_gen:
        df_g = load_data('generators')
        if not df_g.empty:
            st.write("آخر سجلات المولدات الخمسة:")
            st.dataframe(df_g.tail(10))

    with tab_others:
        c1, c2, c3 = st.columns(3)
        # هنا يمكن إضافة ملخص سريع لبقية الأقسام
        st.info("اختر من القائمة الجانبية لإضافة بيانات جديدة أو تصفح الجداول أعلاه.")
