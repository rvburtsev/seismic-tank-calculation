import streamlit as st
import math
import altair as alt
import pandas as pd
import numpy as np

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Сейсмика СН 326-65", layout="wide")
st.title("Расчет сейсмического давления на резервуар")
st.markdown("Согласно **СН 326-65**, раздел 7. Эпюры гидродинамического давления.")

# --- ФУНКЦИЯ РАСЧЕТА K1 (УТОЧНЕННАЯ ПО ГРАФИКУ РИС. 10) ---
def get_K1_value(z_H, h0):
    # Берем 11 точек по высоте для идеально гладкой кривой
    z_pts = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    
    # Оцифрованные значения с высокой точностью
    curves = {
        0.5: [0.35, 0.35, 0.36, 0.37, 0.38, 0.41, 0.45, 0.53, 0.65, 0.82, 1.00],
        0.75:[0.43, 0.43, 0.44, 0.46, 0.47, 0.51, 0.55, 0.63, 0.75, 0.88, 1.00],
        1.0: [0.50, 0.51, 0.52, 0.54, 0.56, 0.60, 0.65, 0.72, 0.82, 0.92, 1.00],
        1.5: [0.58, 0.59, 0.60, 0.62, 0.64, 0.69, 0.75, 0.81, 0.88, 0.95, 1.00],
        2.0: [0.65, 0.66, 0.68, 0.70, 0.74, 0.79, 0.84, 0.88, 0.93, 0.97, 1.00]
    }
    
    # Ограничиваем h0 в пределах графика
    h0 = max(0.5, min(h0, 2.0))
    keys = sorted(curves.keys())
    
    # Находим два ближайших графика для интерполяции
    for i in range(len(keys)-1):
        if keys[i] <= h0 <= keys[i+1]:
            h0_1, h0_2 = keys[i], keys[i+1]
            break
    else:
        h0_1, h0_2 = keys[0], keys[1]
        
    c1 = np.array(curves[h0_1])
    c2 = np.array(curves[h0_2])
    
    # Интерполируем K1 по высоте для двух найденных кривых
    k1_1 = np.interp(z_H, z_pts, c1)
    k1_2 = np.interp(z_H, z_pts, c2)
    
    # Интерполируем между двумя кривыми по h0
    weight = (h0 - h0_1) / (h0_2 - h0_1) if h0_2 != h0_1 else 0
    return k1_1 + weight * (k1_2 - k1_1)

# --- ФУНКЦИЯ ОТРИСОВКИ КРУГОВОЙ ЭПЮРЫ (SVG) ---
def create_svg_epure(p_bottom_kpa):
    size = 600
    cx, cy = size / 2, size / 2
    R_px = 150         
    max_len = 100      
    
    scale = max_len / p_bottom_kpa if p_bottom_kpa > 0 else 0
    
    svg = [f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg" style="background-color: transparent; margin: 0 auto; display: block;">']
    
    # 1. Штриховка
    svg.append('<defs>')
    svg.append('<pattern id="hatch" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">')
    svg.append('<line x1="0" y1="0" x2="0" y2="8" stroke="#4169E1" stroke-width="1.5" />')
    svg.append('</pattern>')
    svg.append('</defs>')
    
    # 2. Оси координат
    svg.append(f'<line x1="{cx - R_px - max_len - 40}" y1="{cy}" x2="{cx + R_px + max_len + 40}" y2="{cy}" stroke="#888" stroke-width="1.5" stroke-dasharray="6,4" />')
    svg.append(f'<line x1="{cx}" y1="{cy - R_px - max_len - 40}" x2="{cx}" y2="{cy + R_px + max_len + 40}" stroke="#888" stroke-width="1.5" stroke-dasharray="6,4" />')
    
    # 3. Заштрихованная область (внешний контур + внутренний круг)
    path_d = f"M {cx + R_px},{cy} " 
    for angle in range(0, 361, 2):
        theta = math.radians(angle)
        p_val = abs(p_bottom_kpa * math.sin(theta))
        L = p_val * scale
        x = cx + (R_px + L) * math.cos(theta)
        y = cy + (R_px + L) * math.sin(theta)
        path_d += f"L {x:.1f},{y:.1f} "
    for angle in range(360, -1, -2):
        theta = math.radians(angle)
        x = cx + R_px * math.cos(theta)
        y = cy + R_px * math.sin(theta)
        path_d += f"L {x:.1f},{y:.1f} "
    path_d += "Z"
    svg.append(f'<path d="{path_d}" fill="url(#hatch)" stroke="none" />')
    
    # 4. Внешняя граница эпюры
    envelope_points = []
    for angle in range(0, 361, 2):
        theta = math.radians(angle)
        p_val = abs(p_bottom_kpa * math.sin(theta))
        L = p_val * scale
        x = cx + (R_px + L) * math.cos(theta)
        y = cy + (R_px + L) * math.sin(theta)
        envelope_points.append(f"{x:.1f},{y:.1f}")
    envelope_path = "M " + " L ".join(envelope_points)
    svg.append(f'<path d="{envelope_path}" fill="none" stroke="#4169E1" stroke-width="2.5" />')
    
    # 5. Стенка резервуара
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{R_px}" stroke="#ffffff" stroke-width="3" fill="none" />')
            
    # 6. Подписи
    svg.append(f'<text x="{cx}" y="{cy - R_px - max_len - 50}" fill="#aaa" font-family="sans-serif" font-size="16" text-anchor="middle">Y</text>')
    svg.append(f'<text x="{cx + R_px + max_len + 50}" y="{cy + 6}" fill="#aaa" font-family="sans-serif" font-size="16" text-anchor="start">X</text>')
    svg.append(f'<text x="{cx - R_px - max_len - 50}" y="{cy + 6}" fill="#aaa" font-family="sans-serif" font-size="16" text-anchor="end">X</text>')
    
    p_text = f"{p_bottom_kpa:.1f} кПа"
    svg.append(f'<text x="{cx}" y="{cy - R_px - max_len - 25}" fill="#4169E1" font-family="sans-serif" font-size="15" font-weight="bold" text-anchor="middle">{p_text}</text>')
    svg.append(f'<text x="{cx}" y="{cy + R_px + max_len + 35}" fill="#4169E1" font-family="sans-serif" font-size="15" font-weight="bold" text-anchor="middle">{p_text}</text>')
    svg.append(f'<text x="{cx - 15}" y="{cy - 10}" fill="#aaa" font-family="sans-serif" font-size="14">0</text>')
    
    svg.append('</svg>')
    return "".join(svg)

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("Исходные данные")
H_input = st.sidebar.number_input("Высота налива (глубина слоя) H, м", min_value=1.0, value=10.0, step=0.5)
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

# Точки по высоте (от дна до уровня налива)
z_points = np.linspace(0, H_input, 100)
p_points = []

for z in z_points:
    z_H = z / H_input
    K1 = get_K1_value(z_H, h0)
    p_val = gamma * r_input * Kc_input * K1
    p_points.append(p_val / 1000) # в кПа

p_bottom = p_points[0]

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Максимальное давление (у дна)", f"{p_bottom:.2f} кПа")
col_m2.metric("Параметр h0 = H/r", f"{h0:.2f}")
col_m3.metric("Сейсмичность", f"{int(Kc_input*10+6)} баллов")

st.markdown("---")

# --- ГРАФИКИ ---
col_graph1, col_graph2 = st.columns([1, 1])

with col_graph1:
    st.subheader("Эпюра по высоте")
    st.markdown("Давление: **pm(z) = γ · r · Kc · K1**")
    
    df_height = pd.DataFrame({"Высота z, м": z_points, "Давление, кПа": p_points})
    
    # Строим эпюру. Благодаря точным K1, она будет иметь прямую нижнюю часть и закругление вверху.
    chart1 = alt.Chart(df_height).mark_area(
        color='crimson', opacity=0.4, line={'color': 'crimson', 'strokeWidth': 2}
    ).encode(
        x=alt.X('Давление, кПа:Q', title='Давление pm(z), кПа'),
        y=alt.Y('Высота z, м:Q', title='Высота z, м', scale=alt.Scale(domain=[0, H_input]))
    ).properties(height=500)
    
    st.altair_chart(chart1, use_container_width=True)

with col_graph2:
    st.subheader("Эпюра давления по окружности")
    st.markdown("Давление: **pm(θ) = pm · sin(θ)**")
    
    svg_image = create_svg_epure(p_bottom)
    st.markdown(svg_image, unsafe_allow_html=True)
