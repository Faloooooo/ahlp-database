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
    category = st.selectbox("القسم:", ["المازوت (قراءات وشراء)", "الغاز (قراءات وشراء)", "المياه", "المولدات", "كهرباء الدولة"])
    
    with st.form("main_form", clear_on_submit=True):
        if category == "المازوت (قراءات وشراء)":
            st.subheader("⛽ جرد الخزانات (cm)")
            main = st.number_input("خزان الطوارئ الرئيسي")
            rec = st.number_input("خزان الاستقبال")
            daily = st.number_input("خزان المولدات (اليومي)")
            boil = st.number_input("خزان البويلر")
            
            st.markdown("---")
            st.subheader("💰 عمليات شراء مازوت جديدة")
            bought_ltr = st.number_input("كمية المازوت المشتراة (Liters)")
            price_usd = st.number_input("إجمالي تكلفة الشراء (USD)")
            # نرسل: القراءات الاربعة، ثم الكمية المشتراة، ثم السعر
            vals = [main, rec, daily, boil, bought_ltr, price_usd]
            s_name = "Fuel_Data"
        
        elif category == "الغاز (قراءات وشراء)":
            st.subheader("🔥 مراقبة الغاز")
            gas_pct = st.number_input("نسبة المخزون الحالي %")
            st.markdown("---")
            st.subheader("🛒 شراء غاز جديد")
            gas_bought = st.number_input("كمية الغاز المشتراة (Liters)")
            gas_price = st.number_input("سعر شراء الغاز (USD)")
            vals = [gas_pct, gas_bought, gas_price]
            s_name = "Gas_Data"

        elif category == "المياه":
            st.subheader("💧 مياه الدولة")
            city_read = st.number_input("عداد مياه الدولة m³")
            city_bill = st.number_input("فاتورة مياه الدولة USD")
            
            st.markdown("---")
            st.subheader("🚚 صهاريج مياه إضافية")
            truck_read = st.number_input("عداد المياه المشتراة m³")
            truck_count = st.number_input("عدد الصهاريج", step=1)
            truck_cost = st.number_input("تكلفة الصهاريج USD")
            
            vals = [city_read, truck_count, 0, truck_cost, city_bill, 0, truck_read]
            s_name = "Water_Data" 

        elif category == "المولدات":
            st.subheader("⚡ قراءات المولدات (1-5)")
            v = []
            for i in range(1, 6):
                c1, c2 = st.columns(2)
                v.append(c1.number_input(f"عداد kWh {i}", key=f"k{i}"))
                v.append(c2.number_input(f"ساعة SMU {i}", key=f"s{i}"))
            vals = v
            s_name = "Generators_kwh"
            
        elif category == "كهرباء الدولة":
            st.subheader("🔌 عدادات EDL")
            vals = [st.number_input("ليل"), st.number_input("ذروة"), st.number_input("نهار"), 
                    st.number_input("تأهيل"), st.number_input("هدر"), st.number_input("اشتراك"), 
                    st.number_input("VAT"), st.number_input("الإجمالي")]
            s_name = "Electricity_Accrual"

        if st.form_submit_button("حفظ وإرسال"):
            if send_to_google(s_name, vals): st.success("تم الحفظ بنجاح")
            else: st.error("فشل الاتصال")

else:
    st.header("📊 ملخص الاستهلاك التلقائي")
    st.info("سيقوم النظام هنا بمقارنة آخر قراءتين تم إدخالهما ليعطيك الصرف الفعلي.")
    # ملاحظة: سنقوم في الخطوة القادمة ببرمجة دالة (Calculate Consumption) 
    # التي تأخذ آخر سطرين من الشيت وتطرحهما من بعضهما.
