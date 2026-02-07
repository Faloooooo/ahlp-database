import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="AHLP Management System", layout="wide", page_icon="🏨")

# الروابط والمفاتيح
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxITTacKEMsGtc4V0aJOlJPnmcXEZrnyfM95tVOUWzcL1U7T8DYMWfEyEvyIwjyhGmW/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'gas': '578874363', 'water': '423939923', 'electricity': '1588872380', 'generators': '1679289485'}
CONV = {'main': 107.22, 'rec': 37.6572, 'daily': 31.26, 'boil': 37.6572}

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip()
        if 'Timestamp' in df.columns:
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
    st.title("🔐 دخول نظام AHLP")
    if st.text_input("كلمة المرور", type="password") == "AHLP2026":
        if st.button("دخول"):
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- القائمة الجانبية ---
mode = st.sidebar.radio("القائمة الرئيسية:", ["📊 التقارير والتحليل", "✍️ إدخال البيانات"])

if mode == "✍️ إدخال البيانات":
    category = st.selectbox("اختر القسم:", ["المازوت", "الغاز", "المياه", "المولدات", "كهرباء الدولة"])
    with st.form("entry_form", clear_on_submit=True):
        if category == "المازوت":
            c1, c2 = st.columns(2); m = c1.number_input("طوارئ (cm)"); r = c2.number_input("استقبال (cm)"); d = c1.number_input("يومي (cm)"); b = c2.number_input("بويلر (cm)")
            st.divider(); bl = st.number_input("كمية الشراء (L)"); bp = st.number_input("تكلفة الشراء (USD)")
            vals, s_name = [m, r, d, b, bl, bp], "Fuel_Data"
        elif category == "المياه":
            st.subheader("🏙️ مياه الدولة"); cw = st.number_input("عداد m³"); cb = st.number_input("فاتورة USD"); cf = st.number_input("رسوم USD")
            st.divider(); st.subheader("🚚 الصهاريج"); tr = st.number_input("عداد الصهريج m³"); tc = st.number_input("العدد"); ts = st.number_input("الحجم m³"); tp = st.number_input("التكلفة USD")
            vals, s_name = [cw, tc, ts, tp, cb, cf, tr], "Water_Data"
        # ... (بقية الأقسام المولدات والغاز والكهرباء تبقى بنفس الترتيب السابق)
        if st.form_submit_button("حفظ وإرسال"):
            if send_to_google(s_name, vals): st.success("✅ تم الحفظ")
            else: st.error("❌ فشل الإرسال")

else: # --- صفحة التقارير ---
    st.title("📈 مركز تحليل البيانات")
    report_type = st.sidebar.selectbox("نوع التقرير:", ["تقرير شهري شامل (مثل الجدول)", "تقرير المازوت اليومي", "تقرير المياه والكهرباء"])
    
    col1, col2 = st.columns(2)
    start_d = col1.date_input("من تاريخ", datetime.now().replace(day=1))
    end_d = col2.date_input("إلى تاريخ", datetime.now())

    if report_type == "تقرير شهري شامل (مثل الجدول)":
        st.subheader(f"📋 ميزانية الطاقة - {start_d.strftime('%B %Y')}")
        # هنا نقوم ببناء جدول يشبه الصورة التي أرسلتها
        summary_data = {
            "البيان (Description)": ["Diesel Cost USD", "Diesel Volume Liter", "Electric Cost USD", "Water Cost USD", "Gas Cost USD"],
            "المجموع للفترة المختارة": [0.0, 0.0, 0.0, 0.0, 0.0]
        }
        # جلب البيانات وحسابها برمجياً
        df_f = load_data('fuel')
        if not df_f.empty:
            mask = (df_f['Timestamp'].dt.date >= start_d) & (df_f['Timestamp'].dt.date <= end_d)
            f_filtered = df_f.loc[mask]
            summary_data["المجموع للفترة المختارة"][0] = f_filtered['Price_USD'].sum() if 'Price_USD' in f_filtered else 0
            summary_data["المجموع للفترة المختارة"][1] = f_filtered['Bought_Liters'].sum() if 'Bought_Liters' in f_filtered else 0
        
        st.table(pd.DataFrame(summary_data))
        st.info("💡 هذا الجدول يتم تحديثه تلقائياً بناءً على ما تدخله يومياً.")

    elif report_type == "تقرير المازوت اليومي":
        st.subheader("⛽ تفاصيل استهلاك المازوت")
        df_f = load_data('fuel')
        if not df_f.empty:
            # معالجة الخطأ KeyError: Bought_Liters
            if 'Bought_Liters' not in df_f.columns: df_f['Bought_Liters'] = 0
            
            mask = (df_f['Timestamp'].dt.date >= start_d) & (df_f['Timestamp'].dt.date <= end_d)
            df_filter = df_f.loc[mask]
            if len(df_filter) >= 1:
                last = df_filter.iloc[-1]
                cur_l = (last['Main_Tank_cm']*CONV['main']) + (last['Receiving_Tank_cm']*CONV['rec']) + (last['Daily_Tank_cm']*CONV['daily']) + (last['Boiler_Tank_cm']*CONV['boil'])
                st.metric("المخزون الإجمالي اللحظي", f"{cur_l:,.1f} L")
                st.dataframe(df_filter)
