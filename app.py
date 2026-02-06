import streamlit as st
import pandas as pd
import plotly.express as px

# إعدادات الصفحة
st.set_page_config(page_title="AHLP Beirut Dashboard", layout="wide")

# روابط البيانات
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {
    'fuel': '1077908569',
    'gas': '578874363',
    'water': '423939923',
    'electricity': '1588872380',
    'generators': '1679289485'
}

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        return df
    except:
        return pd.DataFrame()

# دالة تحويل الغاز
def get_gas_ltr(pct):
    lookup = {10: 106.8, 15: 167.3, 20: 247, 25: 350.5, 30: 454, 35: 574.6, 40: 695.2, 45: 797.6, 50: 900}
    closest = min(lookup.keys(), key=lambda x: abs(x-pct))
    return lookup[closest]

st.title("🏨 نظام إدارة الطاقة - AHLP Beirut")

menu = st.sidebar.radio("القائمة الرئيسية:", ["المازوت ⛽", "الغاز والمياه 💧", "المولدات ⚡"])

if menu == "المازوت ⛽":
    st.header("⛽ مراقبة المخزون الفعلي")
    dff = load_data('fuel')
    if not dff.empty:
        last = dff.iloc[-1]
        main = last['Main_Tank_cm'] * 107
        daily = last['Daily_Tank_cm'] * 31.26
        rec = last['Receiving_Tank_cm'] * 37.6572
        boil = last['Boiler_Tank_cm'] * 37.6572
        total = main + daily + rec + boil
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("خزان الطوارئ", f"{main:,.0f} L")
        c2.metric("خزان المولدات", f"{daily:,.0f} L")
        c3.metric("خزان الاستقبال", f"{rec:,.0f} L")
        c4.metric("خزان البويلر", f"{boil:,.0f} L")
        
        st.subheader(f"إجمالي المازوت: {total:,.1f} لتر")
        # رسم بياني لتاريخ المخزون
        dff['Total_Ltrs'] = (dff['Main_Tank_cm']*107) + (dff['Daily_Tank_cm']*31.26)
        fig = px.line(dff, x='Timestamp', y='Total_Ltrs', title="حركة المخزون الإجمالي")
        st.plotly_chart(fig, use_container_width=True)

elif menu == "الغاز والمياه 💧":
    st.header("💧 الغاز والمياه")
    dfg = load_data('gas')
    dfw = load_data('water')
    
    col1, col2 = st.columns(2)
    with col1:
        if not dfg.empty:
            lg = dfg.iloc[-1]
            gas_ltr = get_gas_ltr(lg['Gas_Storage_Percent'])
            st.metric("مخزون الغاز", f"{gas_ltr} L", f"{lg['Gas_Storage_Percent']}%")
    with col2:
        if not dfw.empty:
            lw = dfw.iloc[-1]
            st.metric("قراءة المياه الحالية", f"{lw['City_Water_Reading']} m³")

elif menu == "المولدات ⚡":
    st.header("⚡ قراءات المولدات")
    dfgen = load_data('generators')
    if not dfgen.empty:
        st.write("آخر القراءات المسجلة للعدادات:")
        st.dataframe(dfgen.tail(5))
