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
    # Готовим данные для Altair
    df_height = pd.DataFrame({"Высота z, м": z_points, "Давление, кПа": [p/1000 for p in p_points]})
    
    # Строим красивую закрашенную эпюру
    chart1 = alt.Chart(df_height).mark_area(
        color='crimson', opacity=0.4, line={'color': 'crimson', 'strokeWidth': 2}
    ).encode(
        x=alt.X('Давление, кПа:Q', title='Давление \(p_m(z)\), кПа'),
        y=alt.Y('Высота z, м:Q', title='Высота \(z\), м', scale=alt.Scale(domain=[0, H_input]))
    ).properties(height=400)
    
    st.altair_chart(chart1, use_container_width=True)

with col_graph2:
    st.subheader("Вид сверху (Рис. 11)")
    # Строим векторы давления (стрелки), как на чертеже
    theta = [math.radians(a) for a in range(0, 361, 10)]
    # Давление по формуле p = p_max * sin(theta)
    p_circle = [abs((p_bottom/1000) * math.sin(t)) for t in theta]
    
    # Переводим в координаты X, Y для рисования
    x_start = [r_input * math.cos(t) for t in theta]
    y_start = [r_input * math.sin(t) for t in theta]
    # Длина вектора зависит от давления (масштабируем для красоты)
    scale_factor = r_input / (p_bottom/1000) * 0.8 if p_bottom > 0 else 0
    x_end = [(r_input - p * scale_factor) * math.cos(t) for p, t in zip(p_circle, theta)]
    y_end = [(r_input - p * scale_factor) * math.sin(t) for p, t in zip(p_circle, theta)]
    
    df_polar = pd.DataFrame({'x': x_start, 'y': y_start, 'x2': x_end, 'y2': y_end})
    
    # Рисуем контур резервуара (окружность)
    circle_theta = [math.radians(a) for a in range(0, 361, 5)]
    df_circle = pd.DataFrame({
        'x': [r_input * math.cos(t) for t in circle_theta],
        'y': [r_input * math.sin(t) for t in circle_theta]
    })
    
    # График векторов
    chart_vec = alt.Chart(df_polar).mark_rule(color='royalblue', strokeWidth=2).encode(
        x='x:Q', y='y:Q', x2='x2:Q', y2='y2:Q'
    )
    
    # График контура
    chart_circle = alt.Chart(df_circle).mark_line(color='black', strokeWidth=2).encode(
        x=alt.X('x:Q', scale=alt.Scale(domain=[-r_input*1.2, r_input*1.2])),
        y=alt.Y('y:Q', scale=alt.Scale(domain=[-r_input*1.2, r_input*1.2]))
    )
    
    # Объединяем графики
    final_polar = (chart_circle + chart_vec).properties(
        height=400,
        # Отключаем сетку и оси для красоты, как на чертеже
    ).configure_axis(grid=False, domain=False, labels=False, ticks=False, title=None)
    
    st.altair_chart(final_polar, use_container_width=True)
