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

# --- ПОСТРОЕНИЕ ГРАФИКОВ (ALTAIR) ---
col_graph1, col_graph2 = st.columns([1, 1])

with col_graph1:
    st.subheader("Эпюра по высоте")
    df_height = pd.DataFrame({"Высота z, м": z_points, "Давление, кПа": [p/1000 for p in p_points]})
    
    chart1 = alt.Chart(df_height).mark_area(
        color='crimson', opacity=0.4, line={'color': 'crimson', 'strokeWidth': 2}
    ).encode(
        x=alt.X('Давление, кПа:Q', title='Давление pm(z), кПа'),
        y=alt.Y('Высота z, м:Q', title='Высота z, м', scale=alt.Scale(domain=[0, H_input]))
    ).properties(height=450)
    
    st.altair_chart(chart1, use_container_width=True)

with col_graph2:
    st.subheader("Эпюра давления по окружности")
    
    # Подготовка данных для векторов
    theta_deg = list(range(0, 360, 10)) # Каждые 10 градусов
    theta_rad = [math.radians(a) for a in theta_deg]
    
    # Формула (21): p = p_max * sin(theta). 
    # Векторы направлены от стенки к центру (показываем давление на стенку)
    # Масштабируем длину вектора для красоты графика
    scale = (r_input * 0.8) / (p_bottom/1000) if p_bottom > 0 else 0
    
    x_wall = [r_input * math.cos(t) for t in theta_rad]
    y_wall = [r_input * math.sin(t) for t in theta_rad]
    
    # Конец вектора (смещение внутрь)
    x_end = [(r_input - abs((p_bottom/1000) * math.sin(t)) * scale) * math.cos(t) for t in theta_rad]
    y_end = [(r_input - abs((p_bottom/1000) * math.sin(t)) * scale) * math.sin(t) for t in theta_rad]
    
    df_vec = pd.DataFrame({'x': x_wall, 'y': y_wall, 'x2': x_end, 'y2': y_end})
    
    # Контур резервуара
    circle_rad = [math.radians(a) for a in range(0, 361, 5)]
    df_circle = pd.DataFrame({
        'x': [r_input * math.cos(t) for t in circle_rad],
        'y': [r_input * math.sin(t) for t in circle_rad]
    })
    
    # Оси X и Y
    df_axes = pd.DataFrame({
        'x': [-r_input*1.3, r_input*1.3, 0, 0],
        'y': [0, 0, -r_input*1.3, r_input*1.3]
    })
    
    # Создаем графики
    chart_circle = alt.Chart(df_circle).mark_line(color='black', strokeWidth=3).encode(
        x=alt.X('x:Q', scale=alt.Scale(domain=[-r_input*1.4, r_input*1.4]), axis=None),
        y=alt.Y('y:Q', scale=alt.Scale(domain=[-r_input*1.4, r_input*1.4]), axis=None)
    )
    
    chart_axes = alt.Chart(df_axes).mark_line(color='gray', strokeWidth=1, strokeDash=[5,5]).encode(
        x='x:Q', y='y:Q'
    )
    
    chart_vec = alt.Chart(df_vec).mark_rule(color='royalblue', strokeWidth=2).encode(
        x='x:Q', y='y:Q', x2='x2:Q', y2='y2:Q'
    )
    
    # Объединяем всё вместе с жесткой привязкой пропорций 1:1 (чтобы был идеальный круг)
    final_polar = (chart_axes + chart_circle + chart_vec).properties(
        width=450, height=450, 
        title=alt.TitleParams("Формула (21): pm(θ) = pm * sin(θ)", anchor='middle')
    ).configure_view(
        strokeWidth=0  # Убираем рамку вокруг графика
    )
    
    st.altair_chart(final_polar)
