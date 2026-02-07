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

# معاملات التحويل الدقيقة (1 سم = كم لتر)
CONV = {'main': 107.22, 'rec': 37.6572, 'daily': 31.26, 'boil': 37.6572}

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip() # تنظيف أسماء الأعمدة من الفراغات
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except Exception as e:
        return pd.DataFrame()

def send_to_google(sheet_name, values):
    try:
        response = requests.post(f"{SCRIPT_URL}?sheet={sheet_name}", data=json.dumps({"values": values}))
        return response.status_code == 200
    except: return False

# --- حماية الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 نظام AHLP - تسجيل الدخول")
    if st.text_input("كلمة المرور", type="password", key="login_pwd") == "AHLP2026":
        if st.button("دخول"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- القائمة الرئيسية ---
mode = st.sidebar.radio("اختر المهمة:", ["📊 ملخص التقارير", "✍️ إدخال بيانات جديدة"])

if mode == "✍️ إدخال بيانات جديدة":
    category = st.selectbox("القسم:", ["المازوت", "الغاز", "المياه", "المولدات", "كهرباء الدولة"])
    with st.form("main_form", clear_on_submit=True):
        if category == "المازوت":
            st.subheader("⛽ جرد الخزانات (cm)")
            main = st.number_input("خزان الطوارئ الرئيسي")
            rec = st.number_input("خزان الاستقبال")
            daily = st.number_input("خزان المولدات")
            boil = st.number_input("خزان البويلر")
            st.markdown("---")
            st.subheader("💰 مشتريات جديدة")
            bought = st.number_input("الكمية المشتراة (Liters)")
            price = st.number_input("التكلفة (USD)")
            vals, s_name = [main, rec, daily, boil, bought, price], "Fuel_Data"
        
        elif category == "الغاز":
            st.subheader("🔥 الخزان المركزي والقوارير")
            vals, s_name = [st.number_input("نسبة الخزان %"), st.number_input("لترات مشتراة"), st.number_input("عدد القوارير"), st.number_input("سعر القوارير")], "Gas_Data"

        elif category == "المياه":
            # --- مياه الدولة في حاوية منفصلة ---
            with st.container():
                st.subheader("🏙️ مياه الدولة (City Water)")
                c_read = st.number_input("قراءة عداد الدولة m³")
                c_bill = st.number_input("فاتورة مياه الدولة USD")
                c_fees = st.number_input("رسوم مياه أخرى USD")
            
            st.markdown("---")
            
            # --- صهاريج المياه في حاوية منفصلة ---
            with st.container():
                st.subheader("🚚 صهاريج مياه إضافية (Trucks)")
                t_read = st.number_input("قراءة عداد الصهاريج (الخاص بالخزان) m³")
                t_count = st.number_input("عدد الصهاريج الواصلة", step=1)
                t_size = st.number_input("حجم الصهريج الواحد m³")
                t_cost = st.number_input("إجمالي تكلفة الصهاريج USD")
            
            vals = [c_read, t_count, t_size, t_cost, c_bill, c_fees, t_read]
            s_name = "Water_Data"

        elif category == "المولدات":
            v = []
            for i in range(1, 6):
                st.subheader(f"⚡ مولد {i}")
                c1, c2 = st.columns(2)
                v.extend([c1.number_input(f"kWh {i}", key=f"k{i}"), c2.number_input(f"SMU {i}", key=f"s{i}")])
            vals, s_name = v, "Generators_kwh"

        elif category == "كهرباء الدولة":
            st.subheader("🔌 عدادات وفاتورة EDL")
            vals, s_name = [st.number_input("ليل"), st.number_input("ذروة"), st.number_input("نهار"), st.number_input("تأهيل"), st.number_input("هدر"), st.number_input("اشتراك"), st.number_input("VAT"), st.number_input("الإجمالي")], "Electricity_Accrual"

        if st.form_submit_button("حفظ وإرسال"):
            if send_to_google(s_name, vals): st.success("✅ تم الحفظ")
            else: st.error("❌ فشل الإرسال")

else: # --- التقارير (تم إصلاح خطأ الصورة) ---
    st.header("📊 مراجعة الاستهلاك")
    col1, col2 = st.columns(2)
    sd = col1.date_input("من", datetime.now().replace(day=1))
    ed = col2.date_input("إلى", datetime.now())

    df_f = load_data('fuel')
    if not df_f.empty and len(df_f) >= 1:
        # تأمين وجود الأعمدة لتجنب خطأ الصورة (KeyError)
        for col in ['Main_Tank_cm', 'Receiving_Tank_cm', 'Daily_Tank_cm', 'Boiler_Tank_cm', 'Bought_Liters']:
            if col not in df_f.columns: df_f[col] = 0
            
        mask = (df_f['Timestamp'].dt.date >= sd) & (df_f['Timestamp'].dt.date <= ed)
        df_filter = df_f.loc[mask]
        
        if not df_filter.empty:
            last = df_filter.iloc[-1]
            prev = df_filter.iloc[0]
            
            cur_l = (last['Main_Tank_cm']*CONV['main']) + (last['Receiving_Tank_cm']*CONV['rec']) + (last['Daily_Tank_cm']*CONV['daily']) + (last['Boiler_Tank_cm']*CONV['boil'])
            old_l = (prev['Main_Tank_cm']*CONV['main']) + (prev['Receiving_Tank_cm']*CONV['rec']) + (prev['Daily_Tank_cm']*CONV['daily']) + (prev['Boiler_Tank_cm']*CONV['boil'])
            
            bought_sum = df_filter['Bought_Liters'].sum()
            cons = (old_l + bought_sum) - cur_l
            
            st.subheader("⛽ ملخص المازوت")
            m1, m2, m3 = st.columns(3)
            m1.metric("المخزون الحالي (L)", f"{cur_l:,.0f}")
            m2.metric("الاستهلاك الصافي", f"{cons:,.0f}")
            m3.metric("مشتريات الفترة", f"{bought_sum:,.0f}")
            
            st.info(f"📍 توزيع الخزانات: طوارئ ({last['Main_Tank_cm']*CONV['main']:,.0f} L) | استقبال ({last['Receiving_Tank_cm']*CONV['rec']:,.0f} L) | يومي ({last['Daily_Tank_cm']*CONV['daily']:,.0f} L) | بويلر ({last['Boiler_Tank_cm']*CONV['boil']:,.0f} L)")
    else:
        st.info("لا توجد بيانات كافية لعرض التقرير.")
