import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Сейсмика СН 326-65", layout="wide")
st.title("Расчет сейсмического давления на резервуар")
st.markdown("Согласно **СН 326-65**, раздел 7 (квазистатический метод)")

# --- ФУНКЦИИ РАСЧЕТА (без изменений) ---
def get_K1(z_H_array, h0):
    z_H_pts = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    curves = {
        0.5: np.array([1.00, 0.96, 0.88, 0.70, 0.40, 0.0]),
        0.75: np.array([1.00, 0.92, 0.80, 0.60, 0.30, 0.0]),
        1.0: np.array([1.00, 0.90, 0.75, 0.50, 0.20, 0.0]),
        1.5: np.array([1.00, 0.85, 0.65, 0.40, 0.15, 0.0]),
        2.0: np.array([1.00, 0.80, 0.60, 0.40, 0.20, 0.0])
    }
    h0_clamped = np.clip(h0, 0.5, 2.0)
    h0_keys = np.array(list(curves.keys()))
    idx = np.searchsorted(h0_keys, h0_clamped)
    if idx == 0:
        h0_1, h0_2 = h0_keys[0], h0_keys[1]
    elif idx == len(h0_keys):
        h0_1, h0_2 = h0_keys[-2], h0_keys[-1]
    else:
        h0_1, h0_2 = h0_keys[idx-1], h0_keys[idx]
        
    f1 = interp1d(z_H_pts, curves[h0_1], kind='cubic', fill_value="extrapolate")
    f2 = interp1d(z_H_pts, curves[h0_2], kind='cubic', fill_value="extrapolate")
    
    K1_1 = f1(z_H_array)
    K1_2 = f2(z_H_array)
    weight = (h0_clamped - h0_1) / (h0_2 - h0_1)
    K1 = K1_1 + weight * (K1_2 - K1_1)
    return np.clip(K1, 0, 1)

def calculate_seismic_pressure(H, r, rho, Kc):
    g = 9.81
    gamma = rho * g
    h0 = H / r
    z = np.linspace(0, H, 100)
    z_H = z / H
    K1 = get_K1(z_H, h0)
    pm_z = gamma * r * Kc * K1
    return z, pm_z

# --- БОКОВАЯ ПАНЕЛЬ (ВВОД ДАННЫХ) ---
st.sidebar.header("Исходные данные")
H_input = st.sidebar.number_input("Высота налива H, м", min_value=1.0, value=10.0, step=0.5)
r_input = st.sidebar.number_input("Радиус резервуара r, м", min_value=1.0, value=15.0, step=0.5)
rho_input = st.sidebar.number_input("Плотность жидкости, кг/м³", min_value=500.0, value=850.0, step=10.0)
Kc_input = st.sidebar.selectbox(
    "Сейсмичность (Kc)", 
    options=[0.1, 0.2, 0.4], 
    format_func=lambda x: f"{x} (соответствует {int(x*10+6)} баллам)"
)

# --- РАСЧЕТ И ВЫВОД ---
z, p = calculate_seismic_pressure(H_input, r_input, rho_input, Kc_input)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Результаты")
    st.info(f"**Максимальное давление у дна:** {p[0]/1000:.2f} кПа")
    st.info(f"**Давление на середине:** {p[len(p)//2]/1000:.2f} кПа")
    st.info(f"**Параметр \(h_0 = H/r\):** {H_input/r_input:.2f}")
    
with col2:
    st.subheader("Эпюра по высоте")
    fig1, ax1 = plt.subplots(figsize=(5, 6))
    ax1.plot(p / 1000, z, color='red', linewidth=2)
    ax1.fill_betweenx(z, 0, p / 1000, color='red', alpha=0.2)
    ax1.set_xlabel('Давление \(p_m(z)\), кПа')
    ax1.set_ylabel('Высота \(z\), м')
    ax1.grid(True)
    ax1.set_ylim(0, H_input)
    st.pyplot(fig1)

st.subheader("Распределение давления по окружности (вид сверху)")
fig2, ax2 = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})
theta = np.linspace(0, 2*np.pi, 100)
p_circle = p[0] * np.sin(theta)
ax2.plot(theta, p_circle / 1000, color='blue', linewidth=2)
ax2.fill(theta, p_circle / 1000, color='blue', alpha=0.2)
ax2.set_title('Формула (21): \(p_m(z, \\theta) = p_m(z) \\cdot \\sin(\\theta)\)')
st.pyplot(fig2)