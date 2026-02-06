import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="AHLP Management System", layout="centered", page_icon="🏨")

# الروابط
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxITTacKEMsGtc4V0aJOlJPnmcXEZrnyfM95tVOUWzcL1U7T8DYMWfEyEvyIwjyhGmW/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

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
            st.subheader("⛽ قراءات المازوت")
            main = st.number_input("خزان الطوارئ (cm)")
            rec = st.number_input("خزان الاستقبال (cm)")
            daily = st.number_input("خزان المولدات (cm)")
            boil = st.number_input("خزان البويلر (cm)")
            price = st.number_input("السعر USD")
            vals = [main, rec, daily, boil, 0, price]
            s_name = "Fuel_Data"
        
        elif category == "الغاز":
            st.subheader("🔥 قراءة الغاز")
            gas_pct = st.number_input("نسبة تخزين الغاز %")
            vals = [gas_pct]
            s_name = "Gas_Data"

        elif category == "المياه":
            st.subheader("💧 مياه الدولة")
            city_read = st.number_input("عداد مياه الدولة m³")
            city_bill = st.number_input("قيمة فاتورة الدولة USD")
            city_fees = st.number_input("رسوم مياه أخرى USD")
            
            st.markdown("---")
            st.subheader("🚚 صهاريج المياه (Extra)")
            truck_read = st.number_input("عداد المياه المشتراة (الخاص بالصهاريج) m³")
            truck_count = st.number_input("عدد الصهاريج (Truck Count)", step=1)
            truck_size = st.number_input("حجم الصهريج الواحد m³")
            truck_cost = st.number_input("إجمالي تكلفة الصهاريج USD")
            
            vals = [city_read, truck_count, truck_size, truck_cost, city_bill, city_fees, truck_read]
            s_name = "Water_Data" 

        elif category == "المولدات":
            st.subheader("⚡ قراءات المولدات الخمسة")
            v = []
            for i in range(1, 6):
                st.markdown(f"**المولد رقم {i}**")
                v.append(st.number_input(f"عداد kWh - مولد {i}", key=f"k{i}"))
                v.append(st.number_input(f"ساعة SMU - مولد {i}", key=f"s{i}"))
            vals = v
            s_name = "Generators_kwh"
            
        elif category == "كهرباء الدولة":
            st.subheader("🔌 عدادات الدولة (EDL)")
            edl1 = st.number_input("EDL 1 - ليل")
            edl2 = st.number_input("EDL 2 - ذروة")
            edl3 = st.number_input("EDL 3 - نهار")
            
            st.markdown("---")
            st.subheader("💸 تفاصيل الفاتورة")
            rehab = st.number_input("رسوم تأهيل USD")
            losses = st.number_input("رسوم هدر USD")
            sub = st.number_input("اشتراك USD")
            vat = st.number_input("VAT USD")
            total = st.number_input("إجمالي الفاتورة USD")
            
            vals = [edl1, edl2, edl3, rehab, losses, sub, vat, total]
            s_name = "Electricity_Accrual"

        if st.form_submit_button("إرسال البيانات"):
            if send_to_google(s_name, vals): st.success(f"✅ تم حفظ بيانات {category} بنجاح")
            else: st.error("❌ فشل الاتصال بالسيرفر")

else:
    st.info("لوحة التقارير قيد التطوير بناءً على بياناتك الجديدة.")
