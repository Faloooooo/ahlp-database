import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="AHLP Management System", layout="wide", page_icon="🏨")

# الروابط والإعدادات
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

# دالة إرسال البيانات
def send_to_google(sheet_name, values):
    try:
        response = requests.post(f"{SCRIPT_URL}?sheet={sheet_name}", data=json.dumps({"values": values}))
        return response.status_code == 200
    except:
        return False

# دالة جلب البيانات
def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except:
        return pd.DataFrame()

# --- حماية التطبيق بكلمة مرور ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 تسجيل الدخول - AHLP")
    pwd = st.text_input("أدخل كلمة المرور", type="password")
    if st.button("دخول"):
        if pwd == "AHLP2026":  # يمكنك تغيير كلمة السر هنا
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("كلمة المرور خاطئة")
    st.stop()

# --- الواجهة الرئيسية بعد الدخول ---
st.sidebar.title("🏨 نظام AHLP المتكامل")
mode = st.sidebar.selectbox("الوضع:", ["📊 لوحة التحكم والتقارير", "✍️ إدخال بيانات جديدة"])

if mode == "✍️ إدخال بيانات جديدة":
    category = st.selectbox("اختر القسم المراد تعبئته:", ["المازوت", "الغاز والمياه", "المولدات"])
    
    with st.form("entry_form"):
        if category == "المازوت":
            main = st.number_input("خزان الطوارئ (cm)", 0.0)
            rec = st.number_input("خزان الاستقبال (cm)", 0.0)
            daily = st.number_input("خزان المولدات (cm)", 0.0)
            boil = st.number_input("خزان البويلر (cm)", 0.0)
            price = st.number_input("سعر المازوت المشتراة (إن وجد)", 0.0)
            vals = [main, rec, daily, boil, 0, price] # ترتيب الأعمدة في الشيت
            s_name = "Fuel_Data"
            
        elif category == "المولدات":
            cat_kwh = st.number_input("عداد CAT (kWh)", 0.0)
            cat_smu = st.number_input("ساعة CAT (SMU)", 0.0)
            perk_kwh = st.number_input("عداد Perkins (kWh)", 0.0)
            perk_smu = st.number_input("ساعة Perkins (SMU)", 0.0)
            vals = [cat_kwh, cat_smu, perk_kwh, perk_smu]
            s_name = "Generators_kwh"

        if st.form_submit_button("حفظ البيانات في السجل"):
            if send_to_google(s_name, vals):
                st.success("✅ تم الحفظ بنجاح في غوغل شيت")
            else:
                st.error("❌ حدث خطأ في الاتصال")

else: # لوحة التحكم والتقارير
    st.sidebar.subheader("📅 فلترة التاريخ")
    start = st.sidebar.date_input("من", datetime(2025, 1, 1))
    end = st.sidebar.date_input("إلى", datetime.now())
    
    tab1, tab2 = st.tabs(["⛽ مخزون المازوت", "⚡ استهلاك الطاقة"])
    
    with tab1:
        df_f = load_data('fuel')
        if not df_f.empty:
            # فلترة حسب التاريخ
            df_f = df_f[(df_f['Timestamp'].dt.date >= start) & (df_f['Timestamp'].dt.date <= end)]
            last = df_f.iloc[-1]
            t_main = last['Main_Tank_cm'] * 107
            t_total = (last['Main_Tank_cm']*107) + (last['Daily_Tank_cm']*31.26)
            
            c1, c2 = st.columns(2)
            c1.metric("المخزون الإجمالي الحالي", f"{t_total:,.0f} L")
            c2.metric("خزان الطوارئ الرئيسي", f"{t_main:,.0f} L")
            
            fig = px.area(df_f, x='Timestamp', y='Main_Tank_cm', title="تذبذب مستوى المازوت الرئيسي")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.write("تقارير المولدات وكفاءة الاستهلاك ستظهر هنا بناءً على المدخلات.")
