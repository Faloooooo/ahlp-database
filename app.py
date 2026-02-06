import streamlit as st
import pandas as pd

# إعدادات الصفحة
st.set_page_config(page_title="AHLP Energy Dashboard", layout="wide")

# الربط بملف Google Sheets
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

# أرقام الصفحات (GIDs) التي استخرجناها سابقاً
GIDS = {
    'fuel': '1077908569',
    'gas': '578874363',
    'water': '423939923',
    'electricity': '1588872380',
    'generators': '1679289485'
}

def load_data(name):
    return pd.read_csv(BASE_URL + GIDS[name])

st.title("🏨 نظام إدارة الطاقة - AHLP Beirut")

# القائمة الجانبية
menu = st.sidebar.selectbox("اختر القسم:", ["المازوت", "الغاز والمياه", "المولدات", "الكهرباء (الدولة)"])

if menu == "المازوت":
    st.header("⛽ مراقبة خزانات المازوت")
    df = load_data('fuel')
    if not df.empty:
        last = df.iloc[-1]
        # المعادلات الفيزيائية
        main = last.get('Main_Tank_cm', 0) * 107
        daily = last.get('Daily_Tank_cm', 0) * 31.26
        receiving = last.get('Receiving_Tank_cm', 0) * 37.6572
        boiler = last.get('Boiler_Tank_cm', 0) * 37.6572
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("الطوارئ (Main)", f"{main:,.0f} L")
        col2.metric("المولدات (Daily)", f"{daily:,.0f} L")
        col3.metric("الاستقبال", f"{receiving:,.0f} L")
        col4.metric("البويلر", f"{boiler:,.0f} L")
        st.divider()
        st.subheader("إجمالي المخزون: " + f"{main+daily+receiving+boiler:,.0f} لتر")

elif menu == "الغاز والمياه":
    st.header("💧 الغاز والمياه")
    # عرض آخر قراءة للغاز والمياه
    st.info("سيتم عرض بيانات الاستهلاك هنا فور اكتمال الإدخالات.")

elif menu == "المولدات":
    st.header("⚡ أداء المولدات (kWh/h)")
    # هنا سنحسب الفرق بين القراءات (Delta)
    st.write("يتم معالجة بيانات الـ SMU والـ kWh...")
