import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# --- 1. الإعدادات ---
st.set_page_config(page_title="Ramada Plaza System", layout="wide")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycby5wzhAdn99OikQFbu8gx2MsNPFWYV0gEE27UxgZPpGJGIQufxPUIe2hEI0tmznG4BF/exec"
SHEET_ID = "1U0zYOYaiUNMd__XGHuF72wIO6JixM5IlaXN-OcIlZH0"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid="

GIDS = {'fuel': '1077908569', 'water': '423939923', 'gas': '578874363', 'electricity': '1588872380', 'generators': '1679289485'}
# الثوابت: Emergency, Receiving, Daily, Boiler
CONV = [107.22, 37.6572, 31.26, 37.6572]

def load_data(name):
    try:
        df = pd.read_csv(BASE_URL + GIDS[name])
        df.columns = df.columns.str.strip()
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        return df
    except: return pd.DataFrame()

# --- 2. نظام الدخول ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 Login")
    if st.text_input("Password", type="password") == "AHLP2026":
        if st.button("Login"): st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- 3. التنقل ---
mode = st.sidebar.radio("القائمة:", ["📊 التقارير", "✍️ إدخال البيانات"])

if mode == "📊 التقارير":
    report = st.sidebar.selectbox("التقرير:", ["تقرير المازوت", "تحليل المياه"])
    sd = st.sidebar.date_input("من", datetime.now()-timedelta(1))
    ed = st.sidebar.date_input("إلى", datetime.now())

    if report == "تقرير المازوت":
        df = load_data('fuel')
        if not df.empty:
            df_filt = df[(df['Timestamp'].dt.date >= sd) & (df['Timestamp'].dt.date <= ed)].sort_values('Timestamp')
            
            if not df_filt.empty:
                last = df_filt.iloc[-1]
                first = df_filt.iloc[0]
                # جلب آخر سعر لتر تم إدخاله (من العمود رقم 6 في شيت المازوت)
                last_price_per_liter = float(df.iloc[-1, 6]) if not pd.isna(df.iloc[-1, 6]) else 0
                
                # --- القسم الأول: المخزون الحالي (الأربعة خزانات) ---
                st.subheader("📍 المخزون الحالي (Liters)")
                c = st.columns(4)
                lbls = ['Emergency', 'Receiving', 'Daily', 'Boiler']
                total_stock = 0
                for i in range(4):
                    # نستخدم i+1 للوصول للأعمدة (1, 2, 3, 4)
                    val = float(last.iloc[i+1]) * CONV[i]
                    total_stock += val
                    c[i].metric(lbls[i], f"{val:,.0f} L")
                
                st.info(f"💰 إجمالي قيمة المخزون الحالي: **${(total_stock * last_price_per_liter / 1000):,.2f}** (تقديري بناءً على آخر سعر)")

                # --- القسم الثاني: المصرف الحالي ---
                st.divider()
                st.subheader(f"📉 المصرف الإجمالي (من {sd} إلى {ed})")
                cs = st.columns(4)
                total_spent = 0
                for i in range(4):
                    usage = max(0, float(first.iloc[i+1]) - float(last.iloc[i+1]))
                    usage_liters = usage * CONV[i]
                    total_spent += usage_liters
                    cs[i].metric(f"{lbls[i]} Spent", f"{usage_liters:,.1f} L")
                
                # إضافة خانة السعر للمصروف
                st.warning(f"💵 تكلفة المازوت المصروف: **${(total_spent * last_price_per_liter / 1000):,.2f}**")

                # الرسم البياني
                st.divider()
                fig = go.Figure()
                clrs = ['red', 'blue', 'green', 'orange']
                for i in range(4):
                    fig.add_trace(go.Scatter(x=df_filt['Timestamp'], y=df_filt.iloc[:, i+1]*CONV[i], name=lbls[i], line=dict(color=clrs[i])))
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("لا توجد بيانات للفترة المختارة")

    elif report == "تحليل المياه":
        # (تقرير المياه يبقى كما هو بدون تغيير)
        dfw = load_data('water')
        if not dfw.empty:
            dff = dfw[(dfw['Timestamp'].dt.date >= sd) & (dfw['Timestamp'].dt.date <= ed)]
            if not dff.empty:
                st.header("💧 نتائج تحليل المياه")
                city_m3 = max(0, float(dff.iloc[-1, 1]) - float(dff.iloc[0, 1]))
                truck_m3 = (dff.iloc[:, 2].astype(float) * dff.iloc[:, 3].astype(float)).sum()
                truck_cost = dff.iloc[:, 4].astype(float).sum()
                city_cost = dff.iloc[:, 5].astype(float).sum() + dff.iloc[:, 6].astype(float).sum()
                c = st.columns(3); c[0].metric("مياه الدولة m³", f"{city_m3:,.1f}"); c[1].metric("مياه الصهاريج m³", f"{truck_m3:,.1f}"); c[2].metric("الإجمالي m³", f"{(city_m3 + truck_m3):,.1f}")
                k = st.columns(3); k[0].metric("تكلفة الدولة", f"${city_cost:,.2f}"); k[1].metric("تكلفة الصهاريج", f"${truck_cost:,.2f}"); k[2].metric("الإجمالي USD", f"${(city_cost + truck_cost):,.2f}")

else:
    # (قسم إدخال البيانات يبقى كما هو)
    st.info("استخدم هذا القسم لإدخال القراءات اليومية لضمان دقة التقارير.")
