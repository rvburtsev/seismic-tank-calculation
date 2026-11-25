import streamlit as st
import math
import pandas as pd

# --- НАСТРОЙКА СТРАНИЦЫ И ЖЕСТКИЙ CSS (ДИЗАЙН GE GAS) ---
st.set_page_config(page_title="ГЕ Газ | Сейсмика резервуаров", page_icon="🛢️", layout="wide")

st.markdown("""
<style>
    /* Импорт шрифта */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap');
    
    /* Жесткое переопределение фона и шрифта */
    html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"] {
        font-family: 'Montserrat', sans-serif !important;
        background: linear-gradient(135deg, #0e1621 0%, #1a2a3a 100%) !important;
        color: #e2e8f0 !important;
    }
    
    /* Убираем белую полосу сверху */
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
    }

    /* Заголовки */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
    }
    
    /* Сайдбар */
    [data-testid="stSidebar"] {
        background-color: #111b26 !important;
        border-right: 1px solid #2d3748 !important;
    }
    [data-testid="stSidebar"] * {
        color: #a0aec0 !important;
    }
    
    /* Карточки с результатами (metrics) */
    [data-testid="stMetric"] {
        background: rgba(26, 42, 58, 0.8) !important;
        border: 1px solid #3b73b9 !important;
        border-radius: 12px !important;
        padding: 15px 20px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
        backdrop-filter: blur(5px);
    }
    [data-testid="stMetricValue"] {
        color: #4da6ff !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #a0aec0 !important;
    }
    
    /* Разделительная линия */
    hr {
        border-color: #2d3748 !important;
    }
</style>
""", unsafe_allow_html=True)

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

# --- ОТРИСОВКА РАЗРЕЗА РЕЗЕРВУАРА (ЛЕВЫЙ ГРАФИК) ---
def create_svg_cross_section(H, r, p_bottom_kpa):
    # Размеры холста SVG
    width, height = 500, 600
    # Координаты основания и центра
    cx, cy = width / 2, height - 50
    tank_w = 200      # Ширина резервуара на картинке
    tank_h = 400      # Максимальная высота резервуара (с бортом)
    max_p_width = 80  # Максимальная ширина эпюры давления
    
    scale_p = max_p_width / p_bottom_kpa if p_bottom_kpa > 0 else 0
    scale_h = tank_h * (H / (H * 1.2)) # Оставляем 20% на пустой борт (прямую часть)
    
    # Точки стен
    left_wall = cx - tank_w / 2
    right_wall = cx + tank_w / 2
    liquid_y = cy - scale_h # Уровень жидкости
    
    svg = [f'<svg width="100%" height="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background-color: transparent;">']
    
    # 1. Штриховка для эпюры давления
    svg.append('<defs>')
    svg.append('<pattern id="hatch_cross" width="6" height="6" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">')
    svg.append('<line x1="0" y1="0" x2="0" y2="6" stroke="#3B73B9" stroke-width="1.5" />')
    svg.append('</pattern>')
    svg.append('</defs>')

    # 2. Ось симметрии (пунктир)
    svg.append(f'<line x1="{cx}" y1="{cy - tank_h - 30}" x2="{cx}" y2="{cy}" stroke="#888" stroke-width="1.5" stroke-dasharray="5,5" />')
    svg.append(f'<text x="{cx + 10}" y="{cy - tank_h - 20}" fill="#888" font-family="sans-serif" font-size="14">Ось Z</text>')
    
    # 3. Днище резервуара
    svg.append(f'<line x1="{left_wall - 60}" y1="{cy}" x2="{right_wall + 60}" y2="{cy}" stroke="#ffffff" stroke-width="3" />')
    # Штриховка грунта под днищем
    for i in range(int(left_wall - 60), int(right_wall + 60), 15):
        svg.append(f'<line x1="{i}" y1="{cy}" x2="{i-10}" y2="{cy+15}" stroke="#888" stroke-width="1" />')

    # 4. Стенки резервуара (включая прямую часть выше уровня жидкости)
    svg.append(f'<line x1="{left_wall}" y1="{cy}" x2="{left_wall}" y2="{cy - tank_h}" stroke="#ffffff" stroke-width="3" />')
    svg.append(f'<line x1="{right_wall}" y1="{cy}" x2="{right_wall}" y2="{cy - tank_h}" stroke="#ffffff" stroke-width="3" />')

    # 5. Уровень жидкости
    svg.append(f'<line x1="{left_wall}" y1="{liquid_y}" x2="{right_wall}" y2="{liquid_y}" stroke="#4da6ff" stroke-width="2" stroke-dasharray="8,4" />')
    svg.append(f'<text x="{right_wall + 10}" y="{liquid_y + 5}" fill="#4da6ff" font-family="sans-serif" font-size="14">Уровень H</text>')

    # 6. Построение эпюры давления (слева и справа)
    # Формируем контуры эпюр
    left_path = f"M {left_wall},{cy} "
    right_path = f"M {right_wall},{cy} "
    
    for i in range(50, -1, -1):
        z_frac = i / 50
        z_m = z_frac * H
        y_pos = cy - (z_frac * scale_h)
        
        # Давление на этой высоте
        p_val = p_bottom_kpa * get_K1_value(z_frac, H/r)
        p_px = p_val * scale_p
        
        left_path += f"L {left_wall - p_px:.1f},{y_pos:.1f} "
        right_path += f"L {right_wall + p_px:.1f},{y_pos:.1f} "

    left_path += f"L {left_wall},{liquid_y} Z"
    right_path += f"L {right_wall},{liquid_y} Z"

    # Заливка эпюр
    svg.append(f'<path d="{left_path}" fill="url(#hatch_cross)" stroke="#3B73B9" stroke-width="2" />')
    svg.append(f'<path d="{right_path}" fill="url(#hatch_cross)" stroke="#3B73B9" stroke-width="2" />')

    # 7. Подписи
    svg.append(f'<text x="{left_wall - max_p_width - 20}" y="{cy - scale_h/2}" fill="#3B73B9" font-family="sans-serif" font-size="15" font-weight="bold" transform="rotate(-90, {left_wall - max_p_width - 20}, {cy - scale_h/2})">Pm(z)</text>')
    svg.append(f'<text x="{cx}" y="{cy - scale_h - 15}" fill="#3B73B9" font-family="sans-serif" font-size="14" text-anchor="middle">{p_bottom_kpa:.1f} кПа</text>')
    
    svg.append('</svg>')
    return "".join(svg)

# --- ОТРИСОВКА КРУГОВОЙ ЭПЮРЫ (ПРАВЫЙ ГРАФИК) ---
def create_svg_epure(p_bottom_kpa):
    size = 600
    cx, cy = size / 2, size / 2
    R_px = 150
    max_len = 100
    scale = max_len / p_bottom_kpa if p_bottom_kpa > 0 else 0
    
    svg = [f'<svg width="100%" height="100%" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg" style="background-color: transparent;">']
    svg.append('<defs>')
    svg.append('<pattern id="hatch_circ" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">')
    svg.append('<line x1="0" y1="0" x2="0" y2="8" stroke="#3B73B9" stroke-width="1.5" />')
    svg.append('</pattern>')
    svg.append('</defs>')
    
    svg.append(f'<line x1="{cx - R_px - max_len - 40}" y1="{cy}" x2="{cx + R_px + max_len + 40}" y2="{cy}" stroke="#888" stroke-width="1.5" stroke-dasharray="6,4" />')
    svg.append(f'<line x1="{cx}" y1="{cy - R_px - max_len - 40}" x2="{cx}" y2="{cy + R_px + max_len + 40}" stroke="#888" stroke-width="1.5" stroke-dasharray="6,4" />')
    
    path_d = f"M {cx + R_px},{cy} " 
    for angle in range(0, 361, 2):
        theta = math.radians(angle)
        L = abs(p_bottom_kpa * math.sin(theta)) * scale
        path_d += f"L {cx + (R_px + L) * math.cos(theta):.1f},{cy + (R_px + L) * math.sin(theta):.1f} "
    for angle in range(360, -1, -2):
        theta = math.radians(angle)
        path_d += f"L {cx + R_px * math.cos(theta):.1f},{cy + R_px * math.sin(theta):.1f} "
    path_d += "Z"
    
    svg.append(f'<path d="{path_d}" fill="url(#hatch_circ)" stroke="none" />')
    
    envelope_points = []
    for angle in range(0, 361, 2):
        theta = math.radians(angle)
        L = abs(p_bottom_kpa * math.sin(theta)) * scale
        envelope_points.append(f"{cx + (R_px + L) * math.cos(theta):.1f},{cy + (R_px + L) * math.sin(theta):.1f}")
    svg.append(f'<path d="M {" L ".join(envelope_points)}" fill="none" stroke="#3B73B9" stroke-width="2.5" />')
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{R_px}" stroke="#ffffff" stroke-width="3" fill="none" />')
            
    svg.append(f'<text x="{cx}" y="{cy - R_px - max_len - 50}" fill="#a0aec0" font-family="sans-serif" font-size="16" text-anchor="middle">Y</text>')
    svg.append(f'<text x="{cx + R_px + max_len + 50}" y="{cy + 6}" fill="#a0aec0" font-family="sans-serif" font-size="16" text-anchor="start">X</text>')
    svg.append(f'<text x="{cx - R_px - max_len - 50}" y="{cy + 6}" fill="#a0aec0" font-family="sans-serif" font-size="16" text-anchor="end">X</text>')
    
    p_text = f"{p_bottom_kpa:.1f} кПа"
    svg.append(f'<text x="{cx}" y="{cy - R_px - max_len - 25}" fill="#4da6ff" font-family="sans-serif" font-size="15" font-weight="bold" text-anchor="middle">{p_text}</text>')
    svg.append(f'<text x="{cx}" y="{cy + R_px + max_len + 35}" fill="#4da6ff" font-family="sans-serif" font-size="15" font-weight="bold" text-anchor="middle">{p_text}</text>')
    svg.append(f'<text x="{cx - 15}" y="{cy - 10}" fill="#a0aec0" font-family="sans-serif" font-size="14">0</text>')
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

# Давление у дна (максимальное)
p_bottom = (gamma * r_input * Kc_input * get_K1_value(0.0, h0)) / 1000 # в кПа

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Максимальное давление (у дна)", f"{p_bottom:.2f} кПа")
col_m2.metric("Параметр h0 = H/r", f"{h0:.2f}")
col_m3.metric("Сейсмичность", f"{int(Kc_input*10+6)} баллов")

st.markdown("---")

# --- ГРАФИКИ ---
col_graph1, col_graph2 = st.columns([1, 1])

with col_graph1:
    st.subheader("Разрез резервуара")
    st.markdown("<p style='color: #a0aec0;'>Эпюра давления на стенки: <b>Pm(z) = γ · r · Kc · K1</b></p>", unsafe_allow_html=True)
    
    # Генерируем и выводим SVG разреза
    svg_cross = create_svg_cross_section(H_input, r_input, p_bottom)
    st.markdown(svg_cross, unsafe_allow_html=True)

with col_graph2:
    st.subheader("Эпюра давления по окружности")
    st.markdown("<p style='color: #a0aec0;'>Распределение по периметру: <b>Pm(θ) = Pm · sin(θ)</b></p>", unsafe_allow_html=True)
    
    # Генерируем и выводим SVG круговой эпюры
    svg_circ = create_svg_epure(p_bottom)
    st.markdown(svg_circ, unsafe_allow_html=True)
