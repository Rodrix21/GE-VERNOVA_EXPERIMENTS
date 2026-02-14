import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Análisis ABC Repuestos", layout="wide")
st.title("📊 Análisis ABC de Repuestos - SAP")

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
    
    # FILTROS DINÁMICOS
    col1, col2, col3 = st.columns(3)
    
    with col1:
        opciones_quien_compra = zm009['Quien Compra'].dropna().unique().tolist()
        quien_compra_sel = st.selectbox("Quien Compra:", opciones_quien_compra)
    
    with col2:
        opciones_tipo_material = zm009['Tipo material'].dropna().unique().tolist()
        tipo_material_sel = st.selectbox("Tipo Material:", opciones_tipo_material)
    
    with col3:
        # Filtrar áreas según quien compra seleccionado
        zm009_filtrado_temp = zm009[zm009['Quien Compra'] == quien_compra_sel]
        opciones_areas = sorted(zm009_filtrado_temp['Area Solicitantes'].dropna().unique().tolist())
        area_seleccionada = st.selectbox("Área Solicitante:", opciones_areas)
    
    if st.button("🔄 Procesar Datos", type="primary"):
        with st.spinner("Aplicando filtros y calculando valores..."):
            
            # APLICAR FILTROS INICIALES
            df = zm009.copy()
            df = df[df['Quien Compra'] == quien_compra_sel]
            df = df[df['Tipo material'] == tipo_material_sel]
            df = df[df['Area Solicitantes'] == area_seleccionada]
            df = df.reset_index(drop=True)
            
            st.write(f"### 📊 Materiales encontrados con filtros iniciales: {len(df)}")
            
            if len(df) == 0:
                st.warning("⚠️ No se encontraron materiales con los filtros aplicados.")
            else:
                # ============================================
                # CALCULAR COLUMNAS BÁSICAS
                # ============================================
                
                # Stock Total (V-NV) (Z)
                df['Stock Total (V-NV)'] = df['Stock Real']
                
                # Porcentual (AD)
                # Fórmula: (Stock Total V-NV - Stock Mínimo) / (Stock Máximo - Stock Mínimo) * 100
                df['Porcentual'] = df.apply(
                    lambda row: ((row['Stock Total (V-NV)'] - row['Stock Mínimo']) / 
                                 (row['Stock Máximo'] - row['Stock Mínimo']) * 100)
                    if (pd.notna(row['Stock Máximo']) and pd.notna(row['Stock Mínimo']) and 
                        row['Stock Máximo'] != row['Stock Mínimo']) else 0,
                    axis=1
                )
                
                # Cant a Comp. (AF)
                # Fórmula: SI(Stock Máximo <> 0; SI(Porcentual <= 10%; Stock Máximo - Stock Total V-NV; "No Comp"); "NA")
                def calcular_cant_comp(row):
                    if pd.isna(row['Stock Máximo']) or row['Stock Máximo'] == 0:
                        return "NA"
                    porcentual = row['Porcentual']
                    if porcentual <= 10:
                        return row['Stock Máximo'] - row['Stock Total (V-NV)']
                    else:
                        return "No Comp"
                
                df['Cant a Comp.'] = df.apply(calcular_cant_comp, axis=1)
                
                # FILTRO 1: Excluir "NA" y "No Comp"
                df = df[~df['Cant a Comp.'].isin(['NA', 'No Comp'])].copy()
                st.write(f"**Después de filtrar Cant a Comp. (solo números):** {len(df)}")
                
                if len(df) == 0:
                    st.warning("⚠️ No hay materiales con cantidad a comprar numérica.")
                else:
                    # Solicitud Pedido (AK)
                    df['Solicitud Pedido'] = df['Material'].apply(
                        lambda x: sc[sc['Cod. SAP'] == x]['Solicitud \nPedido'].values[0] 
                        if len(sc[sc['Cod. SAP'] == x]) > 0 else ""
                    )
                    
                    # FILTRO 2: Solo vacíos (sin solicitud previa)
                    df = df[df['Solicitud Pedido'] == ""].copy()
                    st.write(f"**Después de filtrar Solicitud Pedido (solo vacíos):** {len(df)}")
                    
                    if len(df) == 0:
                        st.warning("⚠️ Todos los materiales ya tienen solicitud/pedido previo.")
                    else:
                        # ============================================
                        # CALCULAR COLUMNAS DE MOVIMIENTOS
                        # ============================================
                        
                        # Cant. Ingreso (AP)
                        df['Cant. Ingreso'] = df['Material'].apply(
                            lambda x: len(mb51[(mb51['Material'] == x) & (mb51['Indicador Debe/Haber'] == 'S')])
                        )
                        
                        # Cant Salida (AQ)
                        df['Cant Salida'] = df['Material'].apply(
                            lambda x: len(mb51[(mb51['Material'] == x) & (mb51['Indicador Debe/Haber'] == 'H')])
                        )
                        
                        # Ingreso y Salida (AR)
                        df['Ingreso y Salida'] = df['Material'].apply(
                            lambda x: len(mb51[mb51['Material'] == x])
                        )
                        
                        # Ingresos y Salidas por año (2022-2026)
                        for year in [2022, 2023, 2024, 2025, 2026]:
                            # Ingreso
                            df[f'Ingreso {year}'] = df.apply(
                                lambda row: mb51[
                                    (mb51['Material'] == row['Material']) &
                                    (mb51['Indicador Debe/Haber'] == 'S') &
                                    (mb51['Tipo material'] == row['Tipo material']) &
                                    (mb51['Ejerc.documento mat.'] == year)
                                ]['Cantidad'].sum(),
                                axis=1
                            )
                            
                            # Salida
                            df[f'Salida {year}'] = df.apply(
                                lambda row: mb51[
                                    (mb51['Material'] == row['Material']) &
                                    (mb51['Indicador Debe/Haber'] == 'H') &
                                    (mb51['Tipo material'] == row['Tipo material']) &
                                    (mb51['Ejerc.documento mat.'] == year)
                                ]['Cantidad'].sum(),
                                axis=1
                            )
                        
                        # Cant. Ingreso (501/561) (BA)
                        df['Cant. Ingreso. (501/561)'] = df.apply(
                            lambda row: mb51[
                                (mb51['Material'] == row['Material']) &
                                (mb51['Indicador Debe/Haber'] == 'S') &
                                (mb51['Tipo material'] == row['Tipo material'])
                            ]['Cantidad'].sum(),
                            axis=1
                        )
                        
                        # Cant. Salida. (BB)
                        df['Cant. Salida.'] = df.apply(
                            lambda row: mb51[
                                (mb51['Material'] == row['Material']) &
                                (mb51['Indicador Debe/Haber'] == 'H') &
                                (mb51['Tipo material'] == row['Tipo material'])
                            ]['Cantidad'].sum(),
                            axis=1
                        )
                        
                        # Cant. Reg. Ingreso (BC)
                        df['Cant. Reg. Ingreso'] = df['Material'].apply(
                            lambda x: len(mb51[(mb51['Material'] == x) & (mb51['Indicador Debe/Haber'] == 'S')])
                        )
                        
                        # Cant. Reg. Salida (BD)
                        df['Cant. Reg. Salida'] = df['Material'].apply(
                            lambda x: len(mb51[(mb51['Material'] == x) & (mb51['Indicador Debe/Haber'] == 'H')])
                        )
                        
                        # Cant. Mov. (BE)
                        df['Cant. Mov.'] = df['Cant. Reg. Ingreso'] + df['Cant. Reg. Salida']
                        
                        # ============================================
                        # ANÁLISIS ABC
                        # ============================================
                        
                        # Ordenar por Cant. Mov. descendente
                        df = df.sort_values('Cant. Mov.', ascending=False).reset_index(drop=True)
                        
                        # Mov. Acumulado (BF)
                        df['Mov. Acumulado'] = df['Cant. Mov.'].cumsum()
                        
                        # % De Mov. Acumulado (BG)
                        total_mov = df['Cant. Mov.'].sum()
                        df['% De Mov. Acumulado'] = (df['Mov. Acumulado'] / total_mov * 100) if total_mov > 0 else 0
                        
                        # Zona (BH)
                        def clasificar_zona(porcentaje):
                            if porcentaje < 80:
                                return 'A'
                            elif porcentaje < 95:
                                return 'B'
                            else:
                                return 'C'
                        
                        df['Zona'] = df['% De Mov. Acumulado'].apply(clasificar_zona)
                        
                        # % Porcentaje (BI)
                        df['% Porcentaje'] = ""
                        
                        for zona in ['A', 'B', 'C']:
                            df_zona = df[df['Zona'] == zona]
                            if len(df_zona) > 0:
                                ultimo_idx = df_zona.index[-1]
                                if zona == 'A':
                                    df.loc[ultimo_idx, '% Porcentaje'] = df.loc[ultimo_idx, '% De Mov. Acumulado']
                                elif zona == 'B':
                                    max_a = df[df['Zona'] == 'A']['% De Mov. Acumulado'].max() if len(df[df['Zona'] == 'A']) > 0 else 0
                                    df.loc[ultimo_idx, '% Porcentaje'] = df.loc[ultimo_idx, '% De Mov. Acumulado'] - max_a
                                elif zona == 'C':
                                    max_b = df[df['Zona'] == 'B']['% De Mov. Acumulado'].max() if len(df[df['Zona'] == 'B']) > 0 else 0
                                    df.loc[ultimo_idx, '% Porcentaje'] = df.loc[ultimo_idx, '% De Mov. Acumulado'] - max_b
                        
                        # ============================================
                        # MOSTRAR TABLA PRINCIPAL
                        # ============================================
                        
                        st.write("---")
                        st.subheader("📋 Tabla Principal - Proceso Completo")
                        
                        columnas_proceso = [
                            'Material', 'Nºmaterial ant.', 'Denominación', 'Quien Compra', 'Area Solicitantes',
                            'Stock Máximo', 'Stock Mínimo', 'Tipo material', 'Stock Total', 
                            'Stock Real', 'Stock Total (V-NV)', 'UM base', 'Porcentual', 
                            'Cant a Comp.', 'Solicitud Pedido', 'Cant. Ingreso', 'Cant Salida',
                            'Ingreso y Salida',
                            'Ingreso 2022', 'Salida 2022',
                            'Ingreso 2023', 'Salida 2023',
                            'Ingreso 2024', 'Salida 2024',
                            'Ingreso 2025', 'Salida 2025',
                            'Ingreso 2026', 'Salida 2026',
                            'Cant. Ingreso. (501/561)', 'Cant. Salida.',
                            'Cant. Reg. Ingreso', 'Cant. Reg. Salida', 'Cant. Mov.',
                            'Mov. Acumulado', '% De Mov. Acumulado', 'Zona', '% Porcentaje'
                        ]
                        
                        st.dataframe(df[columnas_proceso], use_container_width=True, height=500)
                        
                        # ============================================
                        # CUADRO RESUMEN ABC
                        # ============================================
                        
                        st.write("---")
                        st.subheader("📊 Cuadro Resumen - Análisis ABC")
                        
                        resumen = df.groupby('Zona').agg({
                            'Material': 'count',
                            'Cant. Mov.': 'sum'
                        }).reset_index()
                        
                        resumen.columns = ['Zona', 'Nro de Materiales', 'Total Movimientos']
                        
                        # Calcular porcentajes
                        total_materiales = resumen['Nro de Materiales'].sum()
                        total_movimientos = resumen['Total Movimientos'].sum()
                        
                        resumen['% de Materiales'] = (resumen['Nro de Materiales'] / total_materiales * 100).round(2)
                        resumen['% Acumulado'] = resumen['% de Materiales'].cumsum().round(2)
                        resumen['% Movimiento'] = (resumen['Total Movimientos'] / total_movimientos * 100).round(2)
                        resumen['% de Movimiento acumulado'] = resumen['% Movimiento'].cumsum().round(2)
                        
                        # Ordenar por zona A, B, C
                        resumen['Zona'] = pd.Categorical(resumen['Zona'], categories=['A', 'B', 'C'], ordered=True)
                        resumen = resumen.sort_values('Zona')
                        
                        # Mostrar solo columnas solicitadas
                        resumen_final = resumen[['Zona', 'Nro de Materiales', '% de Materiales', 
                                                  '% Acumulado', '% Movimiento', '% de Movimiento acumulado']]
                        
                        st.dataframe(resumen_final, use_container_width=True, hide_index=True)
                        
                        # ============================================
                        # GRÁFICO ABC
                        # ============================================
                        
                        st.write("---")
                        st.subheader("📈 Gráfico Análisis ABC")
                        
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
                                y=resumen['% de Movimiento acumulado'],
                                name='% Movimiento Acumulado',
                                mode='lines+markers+text',
                                line=dict(color='blue', width=3),
                                marker=dict(size=10),
                                text=resumen['% de Movimiento acumulado'].apply(lambda x: f'{x:.1f}%'),
                                textposition='top center'
                            ),
                            secondary_y=True
                        )
                        
                        fig.update_layout(
                            title=f'Análisis ABC - {area_seleccionada}',
                            xaxis_title='Zona',
                            height=500,
                            showlegend=True,
                            legend=dict(x=0.7, y=1.15, orientation='h')
                        )
                        
                        fig.update_yaxes(title_text="% Movimiento", secondary_y=False)
                        fig.update_yaxes(title_text="% Movimiento Acumulado", secondary_y=True, range=[0, 110])
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # ============================================
                        # DESCARGAR DATOS
                        # ============================================
                        
                        st.write("---")
                        st.download_button(
                            label="📥 Descargar tabla completa (CSV)",
                            data=df[columnas_proceso].to_csv(index=False).encode('utf-8'),
                            file_name=f'analisis_abc_{area_seleccionada}.csv',
                            mime='text/csv'
                        )
