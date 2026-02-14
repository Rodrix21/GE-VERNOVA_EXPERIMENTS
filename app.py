import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Análisis ABC Repuestos", layout="wide")
st.title("📊 Análisis ABC de Repuestos - SAP")

# Lista de áreas
AREAS = [
    'EGH - EMBALSE',
    'EGH - GESTION AMBIENTAL',
    'EGH - GESTION SOCIAL',
    'EGH - INSTRUMENTACION CIVIL',
    'EGH - LOGISTICA',
    'EGH - OBRAS CIVILES',
    'EGH - PRODUCCION DE ENERGIA',
    'EGH - SEGURIDAD SST',
    'EGH - SERVICIOS GENERALES',
    'EGH - TALLER ELECTRICO',
    'EGH - TALLER MECANICO',
    'EGH - TIC',
    'GE - ADMINISTRACION',
    'GE - ALMACEN',
    'GE - ELECTRICO',
    'GE - INSTRUMENTACION Y CONTROL',
    'GE - LÍNEA DE TRANSMISIÓN LLTT',
    'GE - MECANICO',
    'GE - OPERRACIONES',
    'GE - SEGURIDAD EHS'
]

# Subir archivo
uploaded_file = st.file_uploader("Sube tu archivo Excel de SAP", type=['xlsx'])

if uploaded_file:
    st.success("✅ Archivo cargado correctamente!")
    
    # Leer las hojas
    with st.spinner("Cargando datos..."):
        zm009 = pd.read_excel(uploaded_file, sheet_name='ZMM009')
        mb51 = pd.read_excel(uploaded_file, sheet_name='MB51')
        sc = pd.read_excel(uploaded_file, sheet_name='SC')
    
    st.info(f"📋 Registros cargados - ZMM009: {len(zm009)} | MB51: {len(mb51)} | SC: {len(sc)}")
    
    # Mostrar vista previa de datos
    with st.expander("👁️ Ver vista previa de las bases de datos"):
        tab1, tab2, tab3 = st.tabs(["ZMM009", "MB51", "SC"])
        
        with tab1:
            st.write(f"**Total registros:** {len(zm009)}")
            st.dataframe(zm009.head(20))
        
        with tab2:
            st.write(f"**Total registros:** {len(mb51)}")
            st.dataframe(mb51.head(20))
        
        with tab3:
            st.write(f"**Total registros:** {len(sc)}")
            st.dataframe(sc.head(20))
    
    # Selector de área
    area_seleccionada = st.selectbox("Selecciona el Área Solicitante:", AREAS)
    
    if st.button("Procesar Datos", type="primary"):
        with st.spinner("Aplicando filtros y calculando valores..."):
            
            # FILTROS
            df = zm009.copy()
            df = df[df['Quien Compra'] == 'EGH - EMP. GENERACIÓN HUALLAGA']
            df = df[df['Tipo material'] == 'UNBW']
            df = df[df['Area Solicitantes'] == area_seleccionada]
            
            # Resetear índice
            df = df.reset_index(drop=True)
            
            st.write(f"### Materiales encontrados: {len(df)}")
            
            if len(df) == 0:
                st.warning("No se encontraron materiales con los filtros aplicados.")
            else:
                # CALCULAR COLUMNAS
                
                # Stock Real (columna Y)
                df['Stock Real Calc'] = df.apply(
                    lambda row: mb51[
                        (mb51['Material'] == row['Material']) & 
                        (mb51['Almacén'] == row['Almacén'])
                    ]['Cantidad'].sum() if pd.notna(row['Material']) else 0,
                    axis=1
                )
                
                # Stock Total V-NV (columna Z) - usando Stock Real de ZMM009
                # Esta columna ya viene calculada en ZMM009, la usamos directamente
                
                # Porcentual (columna AD) - igual que Stock Total V-NV
                df['Porcentual'] = df['Stock Real']
                
                # Cant a Comp (columna AF)
                def calcular_cant_comp(row):
                    if pd.isna(row['Stock Máximo']) or row['Stock Máximo'] == 0:
                        return "NA"
                    porcentaje = (row['Stock Real'] / row['Stock Máximo']) * 100 if row['Stock Máximo'] > 0 else 0
                    if porcentaje <= 10:
                        return row['Stock Máximo'] - row['Stock Real']
                    else:
                        return "No Comp"
                
                df['Cant a Comp.'] = df.apply(calcular_cant_comp, axis=1)
                
                # DIAGNÓSTICO: Mostrar distribución antes de filtrar
                st.write("**Diagnóstico - Distribución de 'Cant a Comp.':**")
                diagnostico = df['Cant a Comp.'].value_counts()
                st.write(diagnostico)
                
                # Filtrar NA y No Comp
                df_filtrado = df[~df['Cant a Comp.'].isin(['NA', 'No Comp'])].copy()
                
                st.write(f"### Después de filtrar NA y No Comp: {len(df_filtrado)} materiales")
                
                # Solicitud Pedido (columna AK)
                df_filtrado['Solicitud Pedido'] = df_filtrado['Material'].apply(
                    lambda x: sc[sc['Cod. SAP'] == x]['Solicitud \nPedido'].values[0] 
                    if len(sc[sc['Cod. SAP'] == x]) > 0 else ""
                )
                
                # Filtrar solo vacíos (sin solicitud)
                df_filtrado = df_filtrado[df_filtrado['Solicitud Pedido'] == ""].copy()
                
                st.write(f"### Materiales a comprar (después de filtros): {len(df_filtrado)}")
                
                if len(df_filtrado) == 0:
                    st.info("No hay materiales que cumplan todos los criterios de compra.")
                else:
                    # CÁLCULOS ADICIONALES (columnas AP-AZ)
                    
                    # Cant Ingreso (AP)
                    df_filtrado['Cant. Ingreso'] = df_filtrado['Material'].apply(
                        lambda x: len(mb51[(mb51['Material'] == x) & (mb51['Indicador Debe/Haber'] == 'S')])
                    )
                    
                    # Cant Salida (AQ)
                    df_filtrado['Cant Salida'] = df_filtrado['Material'].apply(
                        lambda x: len(mb51[(mb51['Material'] == x) & (mb51['Indicador Debe/Haber'] == 'H')])
                    )
                    
                    # Ingreso y Salida (AR)
                    df_filtrado['Ingreso y Salida'] = df_filtrado['Material'].apply(
                        lambda x: len(mb51[mb51['Material'] == x])
                    )
                    
                    # Ingresos y Salidas por año (AS-AZ)
                    for year in [2022, 2023, 2024, 2025]:
                        # Ingreso
                        df_filtrado[f'Ingreso {year}'] = df_filtrado.apply(
                            lambda row: mb51[
                                (mb51['Material'] == row['Material']) &
                                (mb51['Indicador Debe/Haber'] == 'S') &
                                (mb51['Tipo material'] == row['Tipo material']) &
                                (mb51['Ejerc.documento mat.'] == year)
                            ]['Cantidad'].sum(),
                            axis=1
                        )
                        
                        # Salida
                        df_filtrado[f'Salida {year}'] = df_filtrado.apply(
                            lambda row: mb51[
                                (mb51['Material'] == row['Material']) &
                                (mb51['Indicador Debe/Haber'] == 'H') &
                                (mb51['Tipo material'] == row['Tipo material']) &
                                (mb51['Ejerc.documento mat.'] == year)
                            ]['Cantidad'].sum(),
                            axis=1
                        )
                    
                    # ANÁLISIS ABC (columnas BA-BH)
                    
                    # Cant. Ingreso (501/561) (BA)
                    df_filtrado['Cant. Ingreso (501/561)'] = df_filtrado.apply(
                        lambda row: mb51[
                            (mb51['Material'] == row['Material']) &
                            (mb51['Indicador Debe/Haber'] == 'S') &
                            (mb51['Tipo material'] == row['Tipo material'])
                        ]['Cantidad'].sum(),
                        axis=1
                    )
                    
                    # Cant. Salida (BB)
                    df_filtrado['Cant. Salida Total'] = df_filtrado.apply(
                        lambda row: mb51[
                            (mb51['Material'] == row['Material']) &
                            (mb51['Indicador Debe/Haber'] == 'H') &
                            (mb51['Tipo material'] == row['Tipo material'])
                        ]['Cantidad'].sum(),
                        axis=1
                    )
                    
                    # Cant. Reg. Ingreso (BC)
                    df_filtrado['Cant. Reg. Ingreso'] = df_filtrado['Material'].apply(
                        lambda x: len(mb51[(mb51['Material'] == x) & (mb51['Indicador Debe/Haber'] == 'S')])
                    )
                    
                    # Cant. Reg. Salida (BD)
                    df_filtrado['Cant. Reg. Salida'] = df_filtrado['Material'].apply(
                        lambda x: len(mb51[(mb51['Material'] == x) & (mb51['Indicador Debe/Haber'] == 'H')])
                    )
                    
                    # Cant. Mov (BE)
                    df_filtrado['Cant. Mov'] = df_filtrado['Cant. Reg. Ingreso'] + df_filtrado['Cant. Reg. Salida']
                    
                    # Ordenar por Cant. Mov descendente para análisis ABC
                    df_filtrado = df_filtrado.sort_values('Cant. Mov', ascending=False).reset_index(drop=True)
                    
                    # Mov. Acumulado (BF)
                    df_filtrado['Mov. Acumulado'] = df_filtrado['Cant. Mov'].cumsum()
                    
                    # % De Mov. Acumulado (BG)
                    total_mov = df_filtrado['Cant. Mov'].sum()
                    df_filtrado['% De Mov. Acumulado'] = (df_filtrado['Mov. Acumulado'] / total_mov) * 100
                    
                    # Zona (BH)
                    def clasificar_zona(porcentaje):
                        if porcentaje < 80:
                            return 'A'
                        elif porcentaje < 95:
                            return 'B'
                        else:
                            return 'C'
                    
                    df_filtrado['Zona'] = df_filtrado['% De Mov. Acumulado'].apply(clasificar_zona)
                    
                    # CUADRO RESUMEN ABC
                    resumen = df_filtrado.groupby('Zona').agg({
                        'Material': 'count',
                        'Cant. Mov': 'sum'
                    }).reset_index()
                    
                    resumen.columns = ['Zona', 'N° de Materiales', 'Total Movimientos']
                    
                    # Calcular porcentajes
                    total_materiales = resumen['N° de Materiales'].sum()
                    total_movimientos_sum = resumen['Total Movimientos'].sum()
                    
                    resumen['% de Materiales'] = (resumen['N° de Materiales'] / total_materiales * 100).round(2)
                    resumen['% Movimiento'] = (resumen['Total Movimientos'] / total_movimientos_sum * 100).round(2)
                    
                    # % Acumulados
                    resumen['% Materiales Acum.'] = resumen['% de Materiales'].cumsum().round(2)
                    resumen['% Movimiento Acum.'] = resumen['% Movimiento'].cumsum().round(2)
                    
                    # Ordenar por zona A, B, C
                    resumen['Zona'] = pd.Categorical(resumen['Zona'], categories=['A', 'B', 'C'], ordered=True)
                    resumen = resumen.sort_values('Zona')
                    
                    # MOSTRAR RESULTADOS
                    st.write("---")
                    st.subheader("📊 Cuadro Resumen ABC")
                    st.dataframe(resumen, use_container_width=True)
                    
                    # GRÁFICO ABC
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    
                    colores = {'A': 'green', 'B': 'gold', 'C': 'red'}
                    colores_mapeados = resumen['Zona'].map(colores)
                    
                    # Barras: % Movimiento
                    fig.add_trace(
                        go.Bar(
                            x=resumen['Zona'],
                            y=resumen['% Movimiento'],
                            name='% Movimiento',
                            marker_color=colores_mapeados,
                            text=resumen['% Movimiento'].apply(lambda x: f'{x:.1f}%'),
                            textposition='outside'
                        ),
                        secondary_y=False
                    )
                    
                    # Línea: % Movimiento Acumulado
                    fig.add_trace(
                        go.Scatter(
                            x=resumen['Zona'],
                            y=resumen['% Movimiento Acum.'],
                            name='% Movimiento Acumulado',
                            mode='lines+markers+text',
                            line=dict(color='blue', width=3),
                            marker=dict(size=10),
                            text=resumen['% Movimiento Acum.'].apply(lambda x: f'{x:.1f}%'),
                            textposition='top center'
                        ),
                        secondary_y=True
                    )
                    
                    fig.update_layout(
                        title=f'Análisis ABC - {area_seleccionada}',
                        xaxis_title='Zona',
                        height=500,
                        showlegend=True
                    )
                    
                    fig.update_yaxes(title_text="% Movimiento", secondary_y=False)
                    fig.update_yaxes(title_text="% Movimiento Acumulado", secondary_y=True, range=[0, 110])
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # TABLA DE DATOS COMPLETA
                    st.write("---")
                    st.subheader("📋 Tabla de Materiales Procesados")
                    
                    # Seleccionar columnas relevantes para mostrar
                    columnas_mostrar = [
                        'Material', 'Nºmaterial ant.', 'Denominación', 'Stock Máximo', 
                        'Stock Mínimo', 'Stock Total', 'Stock Real', 'Cant a Comp.',
                        'Cant. Mov', 'Mov. Acumulado', '% De Mov. Acumulado', 'Zona'
                    ]
                    
                    st.dataframe(
                        df_filtrado[columnas_mostrar],
                        use_container_width=True,
                        height=400
                    )
                    
                    # Botón de descarga
                    st.download_button(
                        label="📥 Descargar tabla completa (Excel)",
                        data=df_filtrado.to_csv(index=False).encode('utf-8'),
                        file_name=f'analisis_abc_{area_seleccionada}.csv',
                        mime='text/csv'
                    )
