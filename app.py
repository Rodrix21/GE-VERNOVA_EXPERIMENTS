import streamlit as st
import pandas as pd

st.title("📊 Análisis ABC de Repuestos - SAP")
st.write("Sistema de análisis de materiales críticos")

# Subir archivo
uploaded_file = st.file_uploader("Sube tu archivo Excel de SAP", type=['xlsx'])

if uploaded_file:
    st.success("✅ Archivo cargado correctamente!")
    
    # Leer las hojas
    zm009 = pd.read_excel(uploaded_file, sheet_name='ZMM009')
    mb51 = pd.read_excel(uploaded_file, sheet_name='MB51')
    sc = pd.read_excel(uploaded_file, sheet_name='SC')
    
    # Mostrar información básica
    st.subheader("Vista previa de datos")
    
    tab1, tab2, tab3 = st.tabs(["ZMM009", "MB51", "SC"])
    
    with tab1:
        st.write(f"Total de registros: {len(zm009)}")
        st.dataframe(zm009.head(10))
    
    with tab2:
        st.write(f"Total de registros: {len(mb51)}")
        st.dataframe(mb51.head(10))
    
    with tab3:
        st.write(f"Total de registros: {len(sc)}")
        st.dataframe(sc.head(10))
