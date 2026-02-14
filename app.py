import streamlit as st
import pandas as pd

st.set_page_config(page_title="Análisis ABC Repuestos", layout="wide")

st.title("📊 Análisis ABC de Repuestos - SAP")
st.write("Sistema de análisis de materiales críticos")

# Subir archivo
uploaded_file = st.file_uploader("Sube tu archivo Excel de SAP", type=['xlsx'])

if uploaded_file:
    st.success("✅ Archivo cargado correctamente!")
    
    # Leer las hojas
    with st.spinner("Cargando datos..."):
        zm009 = pd.read_excel(uploaded_file, sheet_name='ZMM009')
        mb51 = pd.read_excel(uploaded_file, sheet_name='MB51')
        sc = pd.read_excel(uploaded_file, sheet_name='SC')
    
    # Mostrar información básica
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Registros ZMM009", len(zm009))
    with col2:
        st.metric("Registros MB51", len(mb51))
    with col3:
        st.metric("Registros SC", len(sc))
    
    st.divider()
    
    # Filtros
    st.subheader("🔍 Filtros")
    
    # Lista de áreas
    areas = [
        "EGH - EMBALSE", "EGH - GESTION AMBIENTAL", "EGH - GESTION SOCIAL",
        "EGH - INSTRUMENTACION CIVIL", "EGH - LOGISTICA", "EGH - OBRAS CIVILES",
        "EGH - PRODUCCION DE ENERGIA", "EGH - SEGURIDAD SST", "EGH - SERVICIOS GENERALES",
        "EGH - TALLER ELECTRICO", "EGH - TALLER MECANICO", "EGH - TIC",
        "GE - ADMINISTRACION", "GE - ALMACEN", "GE - ELECTRICO",
        "GE - INSTRUMENTACION Y CONTROL", "GE - LÍNEA DE TRANSMISIÓN LLTT",
        "GE - MECANICO", "GE - OPERRACIONES", "GE - SEGURIDAD EHS"
    ]
    
    area_seleccionada = st.selectbox("Selecciona el Área Solicitante:", areas)
    
    if st.button("🚀 Procesar Datos"):
        st.write(f"Procesando para: **{area_seleccionada}**")
        st.info("Aplicando filtros y calculando valores...")
