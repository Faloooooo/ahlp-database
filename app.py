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

GIDS = {'fuel': '1077908569', 'gas': '578874363', 'water': '423939923', 'electricity': '1588872380', 'generators': '1679289485'}

# معاملات التحويل الدقيقة التي زودتني بها
CONV = {
    'main': 107.22,
    'rec': 37.6572,
    'daily': 31.26,
    'boil': 37.6572
}

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
mode = st.sidebar.radio("اختر المهمة:", ["📊 التقارير الذكية", "✍️ إدخال بيانات جديدة"])

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
            st.subheader("🔥 مراقبة الغاز")
            vals = [st.number_input("نسبة الخزان %"), st.number_input("شراء لترات"), st.number_input("عدد القوارير"), st.number_input("سعر القوارير")]
            s_name = "Gas_Data"

        elif category == "المياه":
            st.subheader("💧 المياه")
            vals = [st.number_input("عداد مياه الدولة m³"), st.number_input("عدد الصهاريج"), st.number_input("حجم الصهريج"), st.number_input("تكلفة الصهاريج"), st.number_input("فاتورة الدولة"), st.number_input("رسوم أخرى"), st.number_input("عداد الصهاريج m³")]
            s_name = "Water_Data"

        elif category == "المولدات":
            v = []
            for i in range(1, 6):
                st.subheader(f"⚡ مولد {i}")
                c1, c2 = st.columns(2)
                v.extend([c1.number_input(f"kWh {i}", key=f"k{i}"), c2.number_input(f"SMU {i}", key=f"s{i}")])
            vals = v
            s_name = "Generators_kwh"

        elif category == "كهرباء الدولة":
            st.subheader("🔌 عدادات EDL")
            vals = [st.number_input("ليل"), st.number_input("ذروة"), st.number_input("نهار"), st.number_input("تأهيل"), st.number_input("هدر"), st.number_input("اشتراك"), st.number_input("VAT"), st.number_input("الإجمالي")]
            s_name = "Electricity_Accrual"

        if st.form_submit_button("حفظ وإرسال"):
            if send_to_google(s_name, vals): st.success("✅ تم الحفظ")
            else: st.error("❌ فشل الإرسال")

else: # --- صفحة التقارير الذكية ---
    st.header("📊 ملخص الاستهلاك والتقارير")
    
    # اختيار فترة التقرير
    col_d1, col_d2 = st.columns(2)
    start_d = col_d1.date_input("من تاريخ", datetime.now().replace(day=1))
    end_d = col_d2.date_input("إلى تاريخ", datetime.now())

    df_f = load_data('fuel')
    if not df_f.empty and len(df_f) >= 2:
        # فلترة حسب التاريخ
        mask = (df_f['Timestamp'].dt.date >= start_d) & (df_f['Timestamp'].dt.date <= end_d)
        df_filtered = df_f.loc[mask]
        
        if not df_filtered.empty:
            last = df_filtered.iloc[-1]
            prev = df_filtered.iloc[0]
            
            # حساب اللترات الحالية
            l_main = last['Main_Tank_cm'] * CONV['main']
            l_rec = last['Receiving_Tank_cm'] * CONV['rec']
            l_daily = last['Daily_Tank_cm'] * CONV['daily']
            l_boil = last['Boiler_Tank_cm'] * CONV['boil']
            total_now = l_main + l_rec + l_daily + l_boil
            
            # حساب اللترات السابقة
            prev_total = (prev['Main_Tank_cm']*CONV['main']) + (prev['Receiving_Tank_cm']*CONV['rec']) + (prev['Daily_Tank_cm']*CONV['daily']) + (prev['Boiler_Tank_cm']*CONV['boil'])
            
            # المشتريات خلال الفترة
            total_bought = df_filtered['Bought_Liters'].sum()
            
            # الاستهلاك الصافي
            consumption = (prev_total + total_bought) - total_now

            st.subheader("⛽ تقرير المازوت التفصيلي")
            c1, c2, c3 = st.columns(3)
            c1.metric("إجمالي المخزون الحالي", f"{total_now:,.1f} L")
            c2.metric("الاستهلاك في هذه الفترة", f"{consumption:,.1f} L")
            c3.metric("إجمالي المشتريات", f"{total_bought:,.1f} L")

            st.markdown("---")
            st.write("📍 **توزيع المخزون اللحظي:**")
            st.write(f"- خزان الطوارئ: {l_main:,.1f} L")
            st.write(f"- خزان الاستقبال: {l_rec:,.1f} L")
            st.write(f"- خزان المولدات: {l_daily:,.1f} L")
            st.write(f"- خزان البويلر: {l_boil:,.1f} L")
            
            # رسم بياني لتطور الاستهلاك
            df_filtered['Total_Liters'] = (df_filtered['Main_Tank_cm']*CONV['main']) + (df_filtered['Receiving_Tank_cm']*CONV['rec']) + (df_filtered['Daily_Tank_cm']*CONV['daily']) + (df_filtered['Boiler_Tank_cm']*CONV['boil'])
            st.line_chart(df_filtered.set_index('Timestamp')['Total_Liters'])
    else:
        st.warning("يرجى إدخال بيانات جديدة لتفعيل التقارير.")
