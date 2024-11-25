import streamlit as st
import pandas as pd
import math
from io import BytesIO
import base64

# Función para cargar inventario
def load_inventory_file():
    inventario_url = "https://docs.google.com/spreadsheets/d/1DVcPPILcqR0sxBZZAOt50lQzoKhoLCEx/export?format=xlsx"
    inventario_api_df = pd.read_excel(inventario_url, sheet_name="Hoja3")
    inventario_api_df.columns = inventario_api_df.columns.str.lower().str.strip()
    return inventario_api_df

# Función para descargar la plantilla (Base64)
def descargar_plantilla():
    plantilla_data = {"cur": [], "codart": []}
    plantilla_df = pd.DataFrame(plantilla_data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        plantilla_df.to_excel(writer, index=False, sheet_name="Plantilla")
    output.seek(0)
    b64 = base64.b64encode(output.read()).decode()
    return b64

# Encabezado común
def render_encabezado():
    st.markdown(
        """
        <h1 style="text-align: center; color: #FF5800; font-family: Arial, sans-serif;">
            RAMEDICAS S.A.S.
        </h1>
        <h3 style="text-align: center; font-family: Arial, sans-serif; color: #3A86FF;">
            Buscador de Alternativas por Código de Artículo FOMAG
        </h3>
        <p style="text-align: center; font-family: Arial, sans-serif; color: #6B6B6B;">
            Esta herramienta te permite buscar y consultar los códigos alternativos de productos con las opciones deseadas de manera eficiente y rápida.
        </p>
        """,
        unsafe_allow_html=True
    )

# Menú de navegación
st.sidebar.title("Menú de Navegación")
menu = st.sidebar.radio("Seleccione una herramienta:", ["Buscador de Alternativas", "Generador de Alternativas"])

# Tool 1: Buscador de Alternativas
if menu == "Buscador de Alternativas":
    render_encabezado()
    
    # Botón para descargar la plantilla
    plantilla_b64 = descargar_plantilla()
    st.markdown(
        f"""
        <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{plantilla_b64}" download="plantilla_faltantes.xlsx">
            <button style="background-color: #FF5800; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer;">
                Descargar plantilla
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

    # Subir archivo de productos faltantes
    uploaded_file = st.file_uploader("Sube un archivo con los productos faltantes (contiene 'codart' y 'cur')", type=["xlsx", "csv"])
    if uploaded_file:
        faltantes_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        inventario_api_df = load_inventory_file()
        alternativas_disponibles_df = procesar_alternativas(faltantes_df, inventario_api_df)
        if not alternativas_disponibles_df.empty:
            st.dataframe(alternativas_disponibles_df)

# Tool 2: Generador de Alternativas
elif menu == "Generador de Alternativas":
    render_encabezado()

    # Subir archivo de faltantes
    uploaded_file = st.file_uploader("Sube tu archivo de faltantes", type="xlsx")
    if uploaded_file:
        faltantes_df = pd.read_excel(uploaded_file)
        inventario_api_df = load_inventory_file()

        # Opciones de selección
        bodegas_disponibles = inventario_api_df['bodega'].unique().tolist()
        bodega_seleccionada = st.multiselect("Seleccione la bodega", options=bodegas_disponibles, default=[])
        columnas_adicionales = st.multiselect(
            "Selecciona columnas adicionales para incluir en el archivo final:",
            options=["presentacionart", "numlote", "fechavencelote"],
            default=[]
        )

        # Procesar alternativas
        resultado_final_df = procesar_faltantes(faltantes_df, inventario_api_df, columnas_adicionales, bodega_seleccionada)
        if not resultado_final_df.empty:
            st.dataframe(resultado_final_df)

            # Botón de descarga
            def to_excel(df):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Alternativas')
                return output.getvalue()

            st.download_button(
                label="Descargar archivo de alternativas",
                data=to_excel(resultado_final_df),
                file_name='alternativas_disponibles.xlsx',
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
