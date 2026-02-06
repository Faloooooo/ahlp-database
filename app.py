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
mode = st.sidebar.radio("اختر المهمة:", ["📊 ملخص الاستهلاك والتقارير", "✍️ إدخال بيانات جديدة"])

if mode == "✍️ إدخال بيانات جديدة":
    category = st.selectbox("القسم:", ["المازوت (قراءات وشراء)", "الغاز (خزان وقوارير)", "المياه", "المولدات", "كهرباء الدولة"])
    
    with st.form("main_form", clear_on_submit=True):
        if category == "المازوت (قراءات وشراء)":
            st.subheader("⛽ جرد الخزانات (cm)")
            main = st.number_input("خزان الطوارئ الرئيسي")
            rec = st.number_input("خزان الاستقبال")
            daily = st.number_input("خزان المولدات (اليومي)")
            boil = st.number_input("خزان البويلر")
            st.markdown("---")
            st.subheader("💰 شراء مازوت جديد")
            bought_ltr = st.number_input("الكمية المشتراة (Liters)")
            price_usd = st.number_input("إجمالي التكلفة (USD)")
            vals = [main, rec, daily, boil, bought_ltr, price_usd]
            s_name = "Fuel_Data"
        
        elif category == "الغاز (خزان وقوارير)":
            st.subheader("🔥 مراقبة الخزان المركزي")
            gas_pct = st.number_input("نسبة الخزان الحالي %")
            gas_bought = st.number_input("شراء غاز للخزان (Liters)")
            
            st.markdown("---")
            st.subheader("🎈 قوارير الغاز (Cylinders)")
            gas_cyl_count = st.number_input("عدد القوارير المشتراة (Qty)", step=1)
            gas_cyl_price = st.number_input("سعر القوارير (USD)")
            
            # ترتيب الإرسال: نسبة الخزان، شراء لترات، عدد القوارير، سعر القوارير
            vals = [gas_pct, gas_bought, gas_cyl_count, gas_cyl_price]
            s_name = "Gas_Data"

        elif category == "المياه":
            st.subheader("💧 مياه الدولة والصهاريج")
            city_read = st.number_input("عداد مياه الدولة m³")
            truck_read = st.number_input("عداد الصهاريج m³")
            truck_cost = st.number_input("تكلفة الصهاريج USD")
            vals = [city_read, 0, 0, truck_cost, 0, 0, truck_read]
            s_name = "Water_Data" 

        elif category == "المولدات":
            v = []
            for i in range(1, 6):
                st.subheader(f"⚡ مولد {i}")
                c1, c2 = st.columns(2)
                v.append(c1.number_input(f"kWh {i}", key=f"k{i}"))
                v.append(c2.number_input(f"SMU {i}", key=f"s{i}"))
            vals = v
            s_name = "Generators_kwh"
            
        elif category == "كهرباء الدولة":
            st.subheader("🔌 عدادات EDL")
            vals = [st.number_input("ليل"), st.number_input("ذروة"), st.number_input("نهار"), 
                    st.number_input("تأهيل"), st.number_input("هدر"), st.number_input("اشتراك"), 
                    st.number_input("VAT"), st.number_input("الإجمالي")]
            s_name = "Electricity_Accrual"

        if st.form_submit_button("حفظ وإرسال"):
            if send_to_google(s_name, vals): st.success("✅ تم حفظ البيانات بنجاح")
            else: st.error("❌ فشل في الإرسال")
