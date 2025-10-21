import streamlit as st
import pandas as pd
from pathlib import Path
import folium
from streamlit_folium import st_folium
from branca.colormap import linear

# --- Configuración de la página de Streamlit ---
st.set_page_config(layout="wide", page_title="Mapa Geológico de Elementos")

# --- Título de la aplicación ---
st.title('🗺️ Visualizador Geológico de Concentración de Elementos')
st.markdown("Utiliza los filtros en el panel de la izquierda para seleccionar un elemento y los tipos de muestra a visualizar.")

# --- Carga y caché de datos ---
@st.cache_data
def load_data(file_path):
    """
    Carga los datos desde un archivo CSV y realiza una limpieza básica.
    """
    try:
        df = pd.read_csv(file_path)
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df.dropna(subset=['latitude', 'longitude', 'tipo_muestra'], inplace=True)
        return df
    except FileNotFoundError:
        st.error(f"Error: El archivo '{file_path}' no se encontró. Asegúrate de que esté en la misma carpeta que la aplicación.")
        return None

# Cargar el DataFrame usando ruta relativa al archivo (funciona en Streamlit Cloud)
base_dir = Path(__file__).parent
data_file = base_dir / 'df_transicion.csv'
df = load_data(data_file)

if df is not None:
    # --- Definición de elementos y tipos de muestra ---
    element_columns = [
        'Li_ppm2', 'Cu_ppm2', 'Co_ppm2', 'Ni_ppm2', 'La_ppm2', 'Ce_ppm2',
        'Pr_ppm2', 'Nd_ppm2', 'Sm_ppm2', 'Eu_ppm2', 'Gd_ppm2', 'Tb_ppm2',
        'Dy_ppm2', 'Ho_ppm2', 'Er_ppm2', 'Tm_ppm2', 'Yb_ppm2', 'Lu_ppm2',
        'Sc_ppm2', 'Y_ppm2'
    ]
    # Nombres más amigables para el menú desplegable
    element_names = [e.split('_')[0] for e in element_columns]
    
    sample_types = sorted(df['tipo_muestra'].unique())

    # --- Barra lateral con los filtros ---
    st.sidebar.header('Filtros de Visualización')

    # 1. Menú desplegable para seleccionar el elemento
    selected_element_name = st.sidebar.selectbox(
        'Selecciona un Elemento:',
        options=element_names,
        index=0  # Selecciona el primer elemento (Li) por defecto
    )
    # Obtener el nombre completo de la columna a partir del nombre corto
    selected_element_col = f"{selected_element_name}_ppm2"

    # 2. Menú de selección múltiple para el tipo de muestra
    selected_sample_types = st.sidebar.multiselect(
        'Selecciona Tipo(s) de Muestra:',
        options=sample_types,
        default=sample_types  # Selecciona todos por defecto
    )
    
    st.sidebar.info("La escala de colores se ajusta dinámicamente a los valores máximos y mínimos del elemento seleccionado en el mapa.")

    # --- Lógica de filtrado de datos ---
    if not selected_sample_types:
        st.warning("Por favor, selecciona al menos un tipo de muestra.")
    else:
        # Filtrar el DataFrame según las selecciones del usuario
        df_filtered = df[df['tipo_muestra'].isin(selected_sample_types)].copy()
        
        # Convertir la columna del elemento a numérico y eliminar valores no válidos o negativos
        df_filtered[selected_element_col] = pd.to_numeric(df_filtered[selected_element_col], errors='coerce')
        df_filtered.dropna(subset=[selected_element_col], inplace=True)
        df_filtered = df_filtered[df_filtered[selected_element_col] >= 0]

        if df_filtered.empty:
            st.warning(f"No hay datos válidos para el elemento '{selected_element_name}' con los filtros seleccionados.")
        else:
            # --- Creación del Mapa Interactivo ---
            
            # Calcular el centro del mapa
            map_center = [df_filtered['latitude'].mean(), df_filtered['longitude'].mean()]
            m = folium.Map(location=map_center, zoom_start=6, tiles="OpenStreetMap")

            # Añadir capa del mapa geológico
            folium.TileLayer(
                tiles='https://tiles.macrostrat.org/carto/{z}/{x}/{y}.png',
                attr='Macrostrat',
                name='Mapa Geológico (Macrostrat)',
                overlay=True,
                control=True,
                opacity=0.6
            ).add_to(m)

            # Crear escala de colores y leyenda
            min_val = df_filtered[selected_element_col].min()
            max_val = df_filtered[selected_element_col].max()

            if max_val > min_val:
                colormap = linear.YlOrRd_09.scale(min_val, max_val)
                colormap.caption = f'Concentración de {selected_element_name} (ppm)'
                m.add_child(colormap)

            # Añadir puntos al mapa
            for _, row in df_filtered.iterrows():
                concentration = row[selected_element_col]
                point_color = colormap(concentration) if 'colormap' in locals() and max_val > min_val else 'blue'

                popup_html = f"""
                <b>Municipio:</b> {row['Municipio']}<br>
                <b>Tipo Muestra:</b> {row['tipo_muestra']}<br>
                <b>{selected_element_name} (ppm):</b> {concentration:.2f}
                """

                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=5,
                    color=point_color,
                    fill=True,
                    fill_color=point_color,
                    fill_opacity=0.7,
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(m)

            # Añadir control de capas
            folium.LayerControl().add_to(m)
            
            # Mostrar el mapa en Streamlit
            st_folium(m, width=None, height=700)