import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="AHLP Management System", layout="wide", page_icon="🏨")

# الروابط
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxITTacKEMsGtc4V0aJOlJPnmcXEZrnyfM95tVOUWzcL1U7T8DYMWfEyEvyIwjyhGmW/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

# الأقسام البرمجية
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

# --- حماية الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 نظام AHLP - تسجيل الدخول")
    if st.text_input("كلمة المرور", type="password") == "AHLP2026":
        if st.button("دخول"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- القائمة الرئيسية ---
mode = st.sidebar.radio("اختر المهمة:", ["📊 التقارير والعرض", "✍️ إدخال بيانات جديدة"])

if mode == "✍️ إدخال بيانات جديدة":
    category = st.selectbox("القسم:", ["المازوت", "الغاز", "المياه", "المولدات", "كهرباء الدولة"])
    
    with st.form("main_form", clear_on_submit=True):
        if category == "المازوت":
            vals = [st.number_input("الطوارئ (cm)"), st.number_input("الاستقبال (cm)"), st.number_input("المولدات (cm)"), st.number_input("البويلر (cm)"), 0, st.number_input("السعر USD")]
            s_name = "Fuel_Data"
        
        elif category == "الغاز":
            vals = [st.number_input("نسبة تخزين الغاز %")]
            s_name = "Gas_Data"

        elif category == "المياه":
            c1, c2 = st.columns(2)
            reading = c1.number_input("قراءة عداد الدولة m³")
            truck_count = c2.number_input("عدد صهاريج المياه (Trucks)", step=1)
            truck_size = c1.number_input("حجم الصهريج m³")
            truck_cost = c2.number_input("تكلفة الصهاريج USD")
            bill_total = c1.number_input("قيمة فاتورة الدولة USD")
            other_fees = c2.number_input("رسوم مياه أخرى USD")
            vals = [reading, truck_count, truck_size, truck_cost, bill_total, other_fees]
            s_name = "Water_Data" 

        elif category == "المولدات":
            st.info("إدخال قراءات المولدات (1-5)")
            c1, c2 = st.columns(2)
            v = []
            for i in range(1, 6):
                v.append(c1.number_input(f"مولد {i} - kWh", key=f"k{i}"))
                v.append(c2.number_input(f"مولد {i} - SMU", key=f"s{i}"))
            vals = v
            s_name = "Generators_kwh"
            
        elif category == "كهرباء الدولة":
            c1, c2 = st.columns(2)
            m1 = c1.number_input("عداد 1 (EDL 1)")
            m2 = c2.number_input("عداد 2 (EDL 2)")
            m3 = c1.number_input("عداد 3 (EDL 3)")
            rehab = c2.number_input("رسوم تأهيل USD")
            losses = c1.number_input("رسوم هدر USD")
            sub = c2.number_input("اشتراك USD")
            vat = c1.number_input("VAT USD")
            total = c2.number_input("إجمالي الفاتورة USD")
            vals = [m1, m2, m3, rehab, losses, sub, vat, total]
            s_name = "Electricity_Accrual"

        if st.form_submit_button("إرسال البيانات"):
            if send_to_google(s_name, vals): st.success(f"✅ تم حفظ بيانات {category} بنجاح")
            else: st.error("❌ فشل الاتصال بالسيرفر")
