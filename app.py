import streamlit as st
import math
import altair as alt
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

# --- ФУНКЦИЯ ДЛЯ ОТРИСОВКИ КРУГОВОЙ ЭПЮРЫ (SVG) С ПОДПИСЯМИ ---
def create_svg_epure(r_m, p_bottom_kpa):
    size = 550 # Немного увеличили размер холста для подписей
    cx, cy = size / 2, size / 2
    R_px = 160 # Радиус бака на картинке в пикселях
    
    max_vec_len = R_px * 0.8
    scale = max_vec_len / p_bottom_kpa if p_bottom_kpa > 0 else 0
    
    svg = [f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg" style="background-color: transparent; margin: 0 auto; display: block;">']
    
    # Оси X и Y (пунктирные)
    svg.append(f'<line x1="{cx - R_px - 50}" y1="{cy}" x2="{cx + R_px + 50}" y2="{cy}" stroke="#888" stroke-width="1" stroke-dasharray="5,5" />')
    svg.append(f'<line x1="{cx}" y1="{cy - R_px - 50}" x2="{cx}" y2="{cy + R_px + 50}" stroke="#888" stroke-width="1" stroke-dasharray="5,5" />')
    
    # Подписи осей
    svg.append(f'<text x="{cx + R_px + 55}" y="{cy + 5}" fill="#aaa" font-family="sans-serif" font-size="14">X</text>')
    svg.append(f'<text x="{cx - 5}" y="{cy - R_px - 55}" fill="#aaa" font-family="sans-serif" font-size="14">Y</text>')
    
    # Подписи значений (давлений)
    # В центре 0
    svg.append(f'<text x="{cx + 5}" y="{cy - 5}" fill="#aaa" font-family="sans-serif" font-size="12">0</text>')
    
    # Вверху и внизу (максимальное давление)
    p_text = f"{p_bottom_kpa:.1f} кПа"
    # Сверху (у стенки)
    svg.append(f'<text x="{cx + 10}" y="{cy - R_px + 15}" fill="#aaa" font-family="sans-serif" font-size="12">{p_text}</text>')
    # Снизу (у стенки)
    svg.append(f'<text x="{cx + 10}" y="{cy + R_px - 5}" fill="#aaa" font-family="sans-serif" font-size="12">{p_text}</text>')
    
    # Черная окружность (стенка резервуара)
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{R_px}" stroke="#ffffff" stroke-width="3" fill="none" />')
    
    # Векторы давления
    for angle in range(0, 360, 10):
        theta = math.radians(angle)
        # Формула (21): p = p_max * sin(theta)
        p_val = abs(p_bottom_kpa * math.sin(theta))
        L = p_val * scale
        
        # Координаты начала (на стенке) и конца (внутри)
        x1 = cx + R_px * math.cos(theta)
        y1 = cy + R_px * math.sin(theta)
        x2 = cx + (R_px - L) * math.cos(theta)
        y2 = cy + (R_px - L) * math.sin(theta)
        
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#4169E1" stroke-width="2.5" />')
        
    svg.append('</svg>')
    return "".join(svg)

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

st.markdown("---")

# --- ПОСТРОЕНИЕ ГРАФИКОВ ---
col_graph1, col_graph2 = st.columns([1, 1])

with col_graph1:
    st.subheader("Эпюра по высоте")
    st.markdown("Давление: **pm(z) = γ · r · Kc · K1**")
    
    df_height = pd.DataFrame({"Высота z, м": z_points, "Давление, кПа": [p/1000 for p in p_points]})
    
    chart1 = alt.Chart(df_height).mark_area(
        color='crimson', opacity=0.4, line={'color': 'crimson', 'strokeWidth': 2}
    ).encode(
        x=alt.X('Давление, кПа:Q', title='Давление pm(z), кПа'),
        y=alt.Y('Высота z, м:Q', title='Высота z, м', scale=alt.Scale(domain=[0, H_input]))
    ).properties(height=480)
    
    st.altair_chart(chart1, use_container_width=True)

with col_graph2:
    st.subheader("Эпюра давления по окружности")
    st.markdown("Давление: **pm(θ) = pm · sin(θ)**")
    
    # Генерируем SVG картинку и выводим её
    svg_image = create_svg_epure(r_input, p_bottom / 1000)
    st.markdown(svg_image, unsafe_allow_html=True)
