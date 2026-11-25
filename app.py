import streamlit as st
import math
import altair as alt
import pandas as pd

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Сейсмика СН 326-65", layout="wide")
st.title("Расчет сейсмического давления на резервуар")
st.markdown("Согласно **СН 326-65**, раздел 7. Эпюры гидродинамического давления.")

# --- ФУНКЦИЯ РАСЧЕТА K1 (УТОЧНЕННАЯ) ---
def get_K1_value(z_H, h0):
    # Добавили промежуточные точки (0.8 и 0.9), чтобы точнее передать форму кривой
    z_pts = [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 1.0]
    
    # Уточненные значения по графику Рис. 10 (для цилиндрических резервуаров)
    # В нижней части K1 падает медленно (образуя прямую эпюру), в верхней - резко
    curves = {
        0.5: [1.00, 0.85, 0.70, 0.55, 0.35, 0.15, 0.0],
        0.75:[1.00, 0.92, 0.83, 0.70, 0.48, 0.25, 0.0],
        1.0: [1.00, 0.97, 0.90, 0.78, 0.55, 0.30, 0.0],
        1.5: [1.00, 0.99, 0.95, 0.85, 0.65, 0.40, 0.0],
        2.0: [1.00, 1.00, 0.98, 0.90, 0.70, 0.45, 0.0]
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

# --- ФУНКЦИЯ ОТРИСОВКИ КРУГОВОЙ ЭПЮРЫ (SVG) ---
def create_svg_epure(p_bottom_kpa):
    size = 600
    cx, cy = size / 2, size / 2
    R_px = 150         
    max_len = 100      
    
    scale = max_len / p_bottom_kpa if p_bottom_kpa > 0 else 0
    
    svg = [f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg" style="background-color: transparent; margin: 0 auto; display: block;">']
    
    # Штриховка
    svg.append('<defs>')
    svg.append('<pattern id="hatch" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">')
    svg.append('<line x1="0" y1="0" x2="0" y2="8" stroke="#4169E1" stroke-width="1.5" />')
    svg.append('</pattern>')
    svg.append('</defs>')
    
    # Оси
    svg.append(f'<line x1="{cx - R_px - max_len - 40}" y1="{cy}" x2="{cx + R_px + max_len + 40}" y2="{cy}" stroke="#888" stroke-width="1.5" stroke-dasharray="6,4" />')
    svg.append(f'<line x1="{cx}" y1="{cy - R_px - max_len - 40}" x2="{cx}" y2="{cy + R_px + max_len + 40}" stroke="#888" stroke-width="1.5" stroke-dasharray="6,4" />')
    
    # Заштрихованная область
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
    
    # Внешний контур
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
    
    # Стенка
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{R_px}" stroke="#ffffff" stroke-width="3" fill="none" />')
            
    # Подписи
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

# Для левого графика берем точки строго до уровня налива (от дна до H)
z_points = [H_input * i / 100 for i in range(101)]
p_points = []

for z in z_points:
    z_H = z / H_input
    K1 = get_K1_value(z_H, h0)
    p_val = gamma * r_input * Kc_input * K1
    p_points.append(p_val / 1000) # сразу в кПа

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
    
    # Строим эпюру. Теперь благодаря точным K1 она должна иметь прямую часть внизу.
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
