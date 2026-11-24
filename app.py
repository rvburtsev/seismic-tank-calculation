import streamlit as st
import math

st.set_page_config(page_title="Сейсмика СН 326-65", layout="wide")
st.title("Расчет сейсмического давления на резервуар")
st.markdown("Согласно **СН 326-65**, раздел 7 (квазистатический метод)")

# --- Функция для получения K1 (упрощенная интерполяция без numpy) ---
def get_K1_value(z_H, h0):
    # Точки с графика (z/H : K1)
    z_pts = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    
    # Кривые для разных h0 (визуальная оценка по графику)
    curves = {
        0.5: [1.00, 0.96, 0.88, 0.70, 0.40, 0.0],
        0.75: [1.00, 0.92, 0.80, 0.60, 0.30, 0.0],
        1.0: [1.00, 0.90, 0.75, 0.50, 0.20, 0.0],
        1.5: [1.00, 0.85, 0.65, 0.40, 0.15, 0.0],
        2.0: [1.00, 0.80, 0.60, 0.40, 0.20, 0.0]
    }
    
    h0 = max(0.5, min(h0, 2.0)) # Ограничиваем h0
    
    # Находим ближайшие кривые
    keys = sorted(curves.keys())
    for i in range(len(keys)-1):
        if keys[i] <= h0 <= keys[i+1]:
            h0_1, h0_2 = keys[i], keys[i+1]
            break
    else:
        h0_1, h0_2 = keys[0], keys[1]
        
    c1, c2 = curves[h0_1], curves[h0_2]
    
    # Интерполяция по z/H для двух кривых
    def interp_z(pts, z):
        for i in range(len(z_pts)-1):
            if z_pts[i] <= z <= z_pts[i+1]:
                t = (z - z_pts[i]) / (z_pts[i+1] - z_pts[i])
                return pts[i] + t * (pts[i+1] - pts[i])
        return pts[-1] if z > 1 else pts[0]
        
    k1_1 = interp_z(c1, z_H)
    k1_2 = interp_z(c2, z_H)
    
    # Интерполяция между кривыми по h0
    weight = (h0 - h0_1) / (h0_2 - h0_1) if h0_2 != h0_1 else 0
    return k1_1 + weight * (k1_2 - k1_1)

# --- Боковая панель ---
st.sidebar.header("Исходные данные")
H_input = st.sidebar.number_input("Высота налива H, м", min_value=1.0, value=10.0, step=0.5)
r_input = st.sidebar.number_input("Радиус резервуара r, м", min_value=1.0, value=15.0, step=0.5)
rho_input = st.sidebar.number_input("Плотность жидкости, кг/м³", min_value=500.0, value=850.0, step=10.0)
Kc_input = st.sidebar.selectbox(
    "Сейсмичность (Kc)", 
    options=[0.1, 0.2, 0.4], 
    format_func=lambda x: f"{x} (соответствует {int(x*10+6)} баллам)"
)

# --- Расчет ---
g = 9.81
gamma = rho_input * g
h0 = H_input / r_input

# Генерируем 20 точек по высоте для графика
z_points = [H_input * i / 20 for i in range(21)]
p_points = []
for z in z_points:
    z_H = z / H_input
    K1 = get_K1_value(z_H, h0)
    p_points.append(gamma * r_input * Kc_input * K1)

p_bottom = p_points[0] # Давление у дна

# --- Вывод результатов ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Результаты")
    st.info(f"**Максимальное давление у дна:** {p_bottom/1000:.2f} кПа")
    mid_idx = len(p_points) // 2
    st.info(f"**Давление на середине:** {p_points[mid_idx]/1000:.2f} кПа")
    st.info(f"**Параметр h0 = H/r:** {h0:.2f}")

with col2:
    st.subheader("Эпюра по высоте")
    # Используем встроенный график Streamlit
    chart_data = {"Высота z, м": z_points, "Давление, кПа": [p/1000 for p in p_points]}
    st.line_chart(chart_data, x="Высота z, м", y="Давление, кПа", color="#FF4B4B")

st.subheader("Распределение давления по окружности (вид сверху)")
# Строим график в полярных координатах с помощью простого bar chart
st.bar_chart(
    {"Давление, кПа": [p_bottom/1000 * math.sin(math.radians(a)) for a in range(0, 360, 10)]},
    height=300
)
st.caption("График показывает давление в кольцевом сечении у дна (формула 21: p = p_max * sin(θ)).")
