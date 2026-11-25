import streamlit as st
import math
import plotly.graph_objects as go
import pandas as pd

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Сейсмика СН 326-65", layout="wide")
st.title("Расчет сейсмического давления на резервуар")
st.markdown("Согласно **СН 326-65**, раздел 7. Эпюры гидродинамического давления.")

# --- ФУНКЦИЯ РАСЧЕТА K1 ---
def get_K1_value(z_H, h0):
    z_pts = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    curves = {
        0.5: [1.00, 0.96, 0.88, 0.70, 0.40, 0.0],
        0.75: [1.00, 0.92, 0.80, 0.60, 0.30, 0.0],
        1.0: [1.00, 0.90, 0.75, 0.50, 0.20, 0.0],
        1.5: [1.00, 0.85, 0.65, 0.40, 0.15, 0.0],
        2.0: [1.00, 0.80, 0.60, 0.40, 0.20, 0.0]
    }
    h0 = max(0.5, min(h0, 2.0))
    keys = sorted(curves.keys())
    for i in range(len(keys)-1):
        if keys[i] <= h0 <= keys[i+1]:
            h0_1, h0_2 = keys[i], keys[i+1]
            break
    else:
        h0_1, h0_2 = keys[0], keys[1]
        
    c1, c2 = curves[h0_1], curves[h0_2]
    
    def interp_z(pts, z):
        for i in range(len(z_pts)-1):
            if z_pts[i] <= z <= z_pts[i+1]:
                t = (z - z_pts[i]) / (z_pts[i+1] - z_pts[i])
                return pts[i] + t * (pts[i+1] - pts[i])
        return pts[-1] if z > 1 else pts[0]
        
    k1_1 = interp_z(c1, z_H)
    k1_2 = interp_z(c2, z_H)
    weight = (h0 - h0_1) / (h0_2 - h0_1) if h0_2 != h0_1 else 0
    return k1_1 + weight * (k1_2 - k1_1)

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("Исходные данные")
H_input = st.sidebar.number_input("Высота налива H, м", min_value=1.0, value=10.0, step=0.5)
r_input = st.sidebar.number_input("Радиус резервуара r, м", min_value=1.0, value=15.0, step=0.5)
rho_input = st.sidebar.number_input("Плотность жидкости, кг/м³", min_value=500.0, value=850.0, step=10.0)
Kc_input = st.sidebar.selectbox(
    "Сейсмичность (Kc)", 
    options=[0.1, 0.2, 0.4], 
    format_func=lambda x: f"{x} ({int(x*10+6)} баллов)"
)

# --- РАСЧЕТ ---
g = 9.81
gamma = rho_input * g
h0 = H_input / r_input

z_points = [H_input * i / 50 for i in range(51)]
p_points = [gamma * r_input * Kc_input * get_K1_value(z / H_input, h0) for z in z_points]
p_bottom = p_points[0]

# --- ВЫВОД РЕЗУЛЬТАТОВ (КАРТОЧКИ) ---
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Максимальное давление (у дна)", f"{p_bottom/1000:.2f} кПа")
col_m2.metric("Параметр h0 = H/r", f"{h0:.2f}")
col_m3.metric("Сейсмичность", f"{int(Kc_input*10+6)} баллов")

# --- ГРАФИКИ ---
st.markdown("---")
col_graph1, col_graph2 = st.columns([1, 1])

with col_graph1:
    st.subheader("Эпюра по высоте")
    # Красивая заливка эпюры
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=[p/1000 for p in p_points], y=z_points,
        fill='tozerox', mode='lines',
        line_color='crimson', name='Давление'
    ))
    fig1.update_layout(
        xaxis_title="Давление \(p_m(z)\), кПа",
        yaxis_title="Высота \(z\), м",
        yaxis=dict(range=[0, H_input], showgrid=True, gridcolor='lightgray'),
        xaxis=dict(showgrid=True, gridcolor='lightgray'),
        plot_bgcolor='white',
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig1, use_container_width=True)

with col_graph2:
    st.subheader("Эпюра по окружности (вид сверху)")
    # Строим полярный график (вид сверху как на Рис. 11)
    # Значения угла от 0 до 360
    theta = [math.radians(a) for a in range(0, 361, 5)]
    
    # Формула (21): p = p_max * sin(theta).
    # Для наглядности берем абсолютное значение, чтобы "бабочка" была ровной
    p_circle = [abs((p_bottom/1000) * math.sin(t)) for t in theta]
    
    fig2 = go.Figure()
    fig2.add_trace(go.Barpolar(
        r=p_circle,
        theta=theta,
        width=[5]*len(theta),
        marker_color='royalblue',
        marker_line_color='black',
        marker_line_width=1,
        opacity=0.8,
        name='Давление'
    ))
    
    # Настраиваем оси полярной системы координат
    fig2.update_layout(
        polar=dict(
            radialaxis=dict(
                title="Давление, кПа",
                angle=90,
                tickangle=90,
                showline=True,
                gridcolor='lightgray'
            ),
            angularaxis=dict(
                direction="clockwise",
                period=360,
                rotation=90, # Поворачиваем так, чтобы ось X была горизонтально (как на чертеже)
                gridcolor='lightgray'
            )
        ),
        margin=dict(l=40, r=40, t=40, b=40),
        showlegend=False
    )
    st.plotly_chart(fig2, use_container_width=True)
    
st.info("Примечание: По оси \(x\) (0° и 180°) давление равно нулю. Максимум давления достигается по оси \(y\) (90° и 270°).")
