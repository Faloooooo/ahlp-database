import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="AHLP Management System", layout="centered", page_icon="🏨")

# الروابط (نفس الروابط السابقة)
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxITTacKEMsGtc4V0aJOlJPnmcXEZrnyfM95tVOUWzcL1U7T8DYMWfEyEvyIwjyhGmW/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'gas': '578874363', 'water': '423939923', 'electricity': '1588872380', 'generators': '1679289485'}

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except: return pd.DataFrame()

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
    # (يبقى كود الإدخال كما هو تماماً في ردنا السابق دون تغيير)
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
            vals = [gas_pct, gas_bought, gas_cyl_count, gas_cyl_price]
            s_name = "Gas_Data"
        elif category == "المياه":
            st.subheader("💧 مياه الدولة والصهاريج")
            city_read = st.number_input("قراءة عداد مياه الدولة m³")
            city_bill = st.number_input("إجمالي فاتورة مياه الدولة USD")
            city_fees = st.number_input("رسوم مياه إضافية USD")
            st.markdown("---")
            st.subheader("🚚 صهاريج المياه (Extra)")
            truck_read = st.number_input("قراءة عداد الصهاريج m³")
            truck_count = st.number_input("عدد الصهاريج", step=1)
            truck_size = st.number_input("حجم الصهريج m³")
            truck_cost = st.number_input("إجمالي تكلفة الصهاريج USD")
            vals = [city_read, truck_count, truck_size, truck_cost, city_bill, city_fees, truck_read]
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
            edl1 = st.number_input("EDL 1 - ليل")
            edl2 = st.number_input("EDL 2 - ذروة")
            edl3 = st.number_input("EDL 3 - نهار")
            st.markdown("---")
            st.subheader("💸 تفاصيل الفاتورة")
            vals = [edl1, edl2, edl3, st.number_input("تأهيل"), st.number_input("هدر"), 
                    st.number_input("اشتراك"), st.number_input("VAT"), st.number_input("الإجمالي")]
            s_name = "Electricity_Accrual"
        if st.form_submit_button("حفظ وإرسال"):
            if send_to_google(s_name, vals): st.success("✅ تم حفظ البيانات بنجاح")
            else: st.error("❌ فشل في الإرسال")

else: # --- صفحة ملخص الاستهلاك والتقارير الذكية ---
    st.header("📊 ملخص الاستهلاك اليومي")
    
    df_fuel = load_data('fuel')
    if len(df_fuel) >= 2:
        # استخراج آخر سطرين
        last_row = df_fuel.iloc[-1]
        prev_row = df_fuel.iloc[-2]
        
        # حساب الكميات باللتر لليوم وأمس
        total_now = (last_row['Main_Tank_cm']*107) + (last_row['Daily_Tank_cm']*31.26)
        total_prev = (prev_row['Main_Tank_cm']*107) + (prev_row['Daily_Tank_cm']*31.26)
        
        # الصرف الصافي (مع مراعاة إذا تم شراء كمية جديدة)
        shira = last_row['Bought_Liters'] if 'Bought_Liters' in last_row else 0
        consumption = (total_prev + shira) - total_now
        
        st.subheader("⛽ تقرير المازوت (آخر 24 ساعة)")
        col1, col2, col3 = st.columns(3)
        col1.metric("المخزون الحالي (L)", f"{total_now:,.0f}")
        col2.metric("الاستهلاك اليومي (L)", f"{consumption:,.0f}", delta=f"{-consumption:,.0f}", delta_color="inverse")
        col3.metric("كمية الشراء", f"{shira:,.0f} L")
        
        # رسم بياني بسيط للتوضيح
        st.line_chart(df_fuel.set_index('Timestamp')[['Main_Tank_cm']])
    else:
        st.warning("بانتظار إدخال قراءة ثانية في الشيت لتفعيل مقارنة الاستهلاك.")
