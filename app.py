import streamlit as st
import pandas as pd
import math
from io import BytesIO

# Función para cargar inventario (compartida entre ambas herramientas)
def load_inventory_file():
    inventario_url = "https://docs.google.com/spreadsheets/d/1DVcPPILcqR0sxBZZAOt50lQzoKhoLCEx/export?format=xlsx"
    inventario_api_df = pd.read_excel(inventario_url, sheet_name="Hoja3")
    inventario_api_df.columns = inventario_api_df.columns.str.lower().str.strip()  # Asegurar nombres consistentes
    return inventario_api_df

# Función para procesar alternativas (Tool 1)
def procesar_alternativas(faltantes_df, inventario_api_df):
    faltantes_df.columns = faltantes_df.columns.str.lower().str.strip()
    if not {'cur', 'codart'}.issubset(faltantes_df.columns):
        st.error("El archivo de faltantes debe contener las columnas: 'cur' y 'codart'")
        return pd.DataFrame()
    cur_faltantes = faltantes_df['cur'].unique()
    alternativas_inventario_df = inventario_api_df[inventario_api_df['cur'].isin(cur_faltantes)]
    columnas_necesarias = ['codart', 'cur', 'nomart', 'cum', 'carta', 'opcion', 'bodega', 'unidadespresentacionlote']
    for columna in columnas_necesarias:
        if columna not in alternativas_inventario_df.columns:
            st.error(f"La columna '{columna}' no se encuentra en el inventario. Verifica el archivo de origen.")
            st.stop()
    alternativas_inventario_df['opcion'] = alternativas_inventario_df['opcion'].fillna(0).astype(int)
    alternativas_disponibles_df = pd.merge(
        faltantes_df[['cur', 'codart']],
        alternativas_inventario_df[columnas_necesarias],
        on=['cur', 'codart'],
        how='inner'
    ).drop_duplicates()
    return alternativas_disponibles_df

# Función para procesar faltantes (Tool 2)
def procesar_faltantes(faltantes_df, inventario_api_df, columnas_adicionales, bodega_seleccionada):
    faltantes_df.columns = faltantes_df.columns.str.lower().str.strip()
    inventario_api_df.columns = inventario_api_df.columns.str.lower().str.strip()
    columnas_necesarias = {'cur', 'codart', 'faltante', 'embalaje'}
    if not columnas_necesarias.issubset(faltantes_df.columns):
        st.error(f"El archivo de faltantes debe contener las columnas: {', '.join(columnas_necesarias)}")
        return pd.DataFrame()
    cur_faltantes = faltantes_df['cur'].unique()
    alternativas_inventario_df = inventario_api_df[inventario_api_df['cur'].isin(cur_faltantes)]
    if bodega_seleccionada:
        alternativas_inventario_df = alternativas_inventario_df[alternativas_inventario_df['bodega'].isin(bodega_seleccionada)]
    alternativas_disponibles_df = alternativas_inventario_df[alternativas_inventario_df['unidadespresentacionlote'] > 0]
    alternativas_disponibles_df.rename(columns={
        'codart': 'codart_alternativa',
        'opcion': 'opcion_alternativa',
        'embalaje': 'embalaje_alternativa'
    }, inplace=True)
    alternativas_disponibles_df = pd.merge(
        faltantes_df[['cur', 'codart', 'faltante', 'embalaje']],
        alternativas_disponibles_df,
        on='cur',
        how='inner'
    )
    alternativas_disponibles_df['cantidad_necesaria'] = alternativas_disponibles_df.apply(
        lambda row: math.ceil(row['faltante'] * row['embalaje'] / row['embalaje_alternativa'])
        if pd.notnull(row['embalaje']) and pd.notnull(row['embalaje_alternativa']) and row['embalaje_alternativa'] > 0
        else None,
        axis=1
    )
    alternativas_disponibles_df.sort_values(by=['codart', 'unidadespresentacionlote'], inplace=True)
    mejores_alternativas = []
    for codart_faltante, group in alternativas_disponibles_df.groupby('codart'):
        faltante_cantidad = group['faltante'].iloc[0]
        mejor_opcion_bodega = group[group['unidadespresentacionlote'] >= faltante_cantidad]
        mejor_opcion = mejor_opcion_bodega.head(1) if not mejor_opcion_bodega.empty else group.nlargest(1, 'unidadespresentacionlote')
        mejores_alternativas.append(mejor_opcion.iloc[0])
    resultado_final_df = pd.DataFrame(mejores_alternativas)
    columnas_finales = ['cur', 'codart', 'faltante', 'embalaje', 'codart_alternativa', 'opcion_alternativa', 
                        'embalaje_alternativa', 'cantidad_necesaria', 'unidadespresentacionlote', 'bodega', 'carta']
    columnas_finales.extend([col.lower() for col in columnas_adicionales])
    return resultado_final_df[[col for col in columnas_finales if col in resultado_final_df.columns]]

# Menú de navegación
st.sidebar.title("Menú de Navegación")
menu = st.sidebar.radio("Seleccione una herramienta:", ["Buscador de Alternativas", "Generador de Alternativas"])

# Tool 1: Buscador de Alternativas
if menu == "Buscador de Alternativas":
    st.title("Buscador de Alternativas por Código de Artículo")
    uploaded_file = st.file_uploader("Sube un archivo con los productos faltantes (contiene 'codart' y 'cur')", type=["xlsx", "csv"])
    if uploaded_file:
        faltantes_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        inventario_api_df = load_inventory_file()
        alternativas_disponibles_df = procesar_alternativas(faltantes_df, inventario_api_df)
        if not alternativas_disponibles_df.empty:
            st.dataframe(alternativas_disponibles_df)

# Tool 2: Generador de Alternativas
elif menu == "Generador de Alternativas":
    st.title("Generador de Alternativas para Faltantes")
    uploaded_file = st.file_uploader("Sube tu archivo de faltantes", type="xlsx")
    if uploaded_file:
        faltantes_df = pd.read_excel(uploaded_file)
        inventario_api_df = load_inventory_file()
        bodegas_disponibles = inventario_api_df['bodega'].unique().tolist()
        bodega_seleccionada = st.multiselect("Seleccione la bodega", options=bodegas_disponibles, default=[])
        columnas_adicionales = st.multiselect(
            "Selecciona columnas adicionales para incluir en el archivo final:",
            options=["presentacionart", "numlote", "fechavencelote"],
            default=[]
        )
        resultado_final_df = procesar_faltantes(faltantes_df, inventario_api_df, columnas_adicionales, bodega_seleccionada)
        if not resultado_final_df.empty:
            st.dataframe(resultado_final_df)
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
