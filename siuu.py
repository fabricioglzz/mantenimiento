# ============================================
# DASHBOARD MANTENIMIENTO MAQUINARIA
# Usa:
#   - TABLA1_FINAL_CON_ID.csv  (fallas)
#   - TABLA2DASH.csv           (tiempo entre fallas)
#   - TABLA3_FINAL.csv         (predicciones)
# Carpeta: misma carpeta donde está este app.py
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# -----------------------------
# CONFIGURACIÓN DE LA PÁGINA
# -----------------------------
st.set_page_config(
    page_title="Dashboard mantenimiento",
    layout="wide"
)

# -----------------------------
# RUTA BASE (MISMO DIRECTORIO)
# -----------------------------
BASE_DIR = Path(__file__).parent

# TABLA 1 (fallas categóricas)
COL_ID_FALLA = "ID_Falla"
COL_MAQ      = "Maquina"      # la vamos a crear renombrando "Machine Name"
COL_TURNO    = "Turno"        # la vamos a crear renombrando "Shift"
COL_UBIC     = "EQ_Type"      # de "EQ Type"

# TABLA 2 (tiempos entre fallas)
COL_IDX_TIEMPO           = "Indice_Tiempo"
COL_TIEMPO_ENTRE_FALLAS  = "Tiempo_Entre_Fallas"

# TABLA 3 (predicciones)
COL_FORECAST = "Forecast"


# -----------------------------
# FUNCIÓN DE CARGA DE DATOS
# -----------------------------
@st.cache_data
def load_data():
    """Carga las tres tablas desde la misma carpeta que app.py y ajusta nombres."""

    # ----- TABLA 1 -----
    t1_path = BASE_DIR / "TABLA1_FINAL_CON_ID.csv"
    tabla1 = pd.read_csv(t1_path, encoding="latin1")

    # Renombrar columnas para que sean consistentes
    tabla1 = tabla1.rename(columns={
        "Machine Name": "Maquina",
        "Shift": "Turno",
        "EQ Type": "EQ_Type"
    })
    # Normalizar máquinas a MAYÚSCULAS
    tabla1["Maquina"] = tabla1["Maquina"].astype(str).str.upper()

    # ----- TABLA 2 -----
    t2_path = BASE_DIR / "TABLA2DASH.csv"
    tabla2 = pd.read_csv(t2_path, encoding="latin1")

    if "Maquina" in tabla2.columns:
        tabla2["Maquina"] = tabla2["Maquina"].astype(str).str.upper()

    tabla2[COL_TIEMPO_ENTRE_FALLAS] = pd.to_numeric(
        tabla2[COL_TIEMPO_ENTRE_FALLAS], errors="coerce"
    )
    tabla2[COL_IDX_TIEMPO] = pd.to_numeric(
        tabla2[COL_IDX_TIEMPO], errors="coerce"
    )

    # ----- TABLA 3 -----
    t3_path = BASE_DIR / "TABLA3_FINAL.csv"
    tabla3 = pd.read_csv(t3_path, encoding="latin1")

    if "Maquina" in tabla3.columns:
        tabla3["Maquina"] = tabla3["Maquina"].astype(str).str.upper()

    tabla3[COL_FORECAST] = pd.to_numeric(
        tabla3[COL_FORECAST], errors="coerce"
    )
    tabla3[COL_IDX_TIEMPO] = pd.to_numeric(
        tabla3[COL_IDX_TIEMPO], errors="coerce"
    )

    return tabla1, tabla2, tabla3


# -----------------------------
# FUNCIÓN PRINCIPAL
# -----------------------------
def main():
    st.title("📊 Dashboard de mantenimiento y fallas por máquina")
    st.markdown(
        """
        Este dashboard resume el comportamiento de las **fallas de maquinaria**:

        - Distribución por **turno** y **EQ Type / tipo de equipo** (TABLA 1)  
        - Comportamiento del **tiempo entre fallas** (TABLA 2)  
        - **Predicciones** de tiempo entre fallas para algunas máquinas (TABLA 3)  
        """
    )

    # ===== CARGA DE DATOS =====
    try:
        tabla1, tabla2, tabla3 = load_data()
    except FileNotFoundError as e:
        st.error(f"No se encontró algún archivo .csv. Detalle: {e}")
        st.stop()

    # ===== SIDEBAR: FILTROS =====
    st.sidebar.header("Filtros")

    # Opciones de clusters categóricos (desde TABLA 1)
    if "Cluster" in tabla1.columns:
        clusters_disp = sorted(tabla1["Cluster"].dropna().astype(str).unique())
    else:
        clusters_disp = []

    cluster_sel = st.sidebar.selectbox(
        "Selecciona el cluster categórico",
        options=["Todos"] + clusters_disp
    )

    # Máquinas disponibles según cluster seleccionado
    if cluster_sel == "Todos" or "Cluster" not in tabla1.columns:
        maqs_t1 = tabla1["Maquina"].dropna().unique()
    else:
        maqs_t1 = tabla1.loc[tabla1["Cluster"].astype(str) == cluster_sel, "Maquina"].dropna().unique()

    maqs_t2 = tabla2["Maquina"].dropna().unique()
    maqs_t3 = tabla3["Maquina"].dropna().unique()

    maquinas = sorted(set(maqs_t1) | set(maqs_t2) | set(maqs_t3))

    maquina_sel = st.sidebar.selectbox(
        "Selecciona la máquina para detalle",
        options=["Todas"] + list(maquinas)
    )

    # ===== APLICAR FILTROS A LAS TABLAS =====
    t1 = tabla1.copy()
    t2 = tabla2.copy()
    t3 = tabla3.copy()

    # Filtro por cluster categórico (TABLA 1) → define conjunto de máquinas del cluster
    if cluster_sel != "Todos" and "Cluster" in t1.columns:
        t1 = t1[t1["Cluster"].astype(str) == cluster_sel]
        maquinas_cluster = t1["Maquina"].dropna().unique()
        # Filtrar TABLA 2 y 3 por las máquinas de ese cluster
        t2 = t2[t2["Maquina"].isin(maquinas_cluster)]
        t3 = t3[t3["Maquina"].isin(maquinas_cluster)]

    # Filtro adicional por máquina (si se eligió una específica)
    if maquina_sel != "Todas":
        t1 = t1[t1["Maquina"] == maquina_sel]
        t2 = t2[t2["Maquina"] == maquina_sel]
        t3 = t3[t3["Maquina"] == maquina_sel]

    # =========================
    # SECCIÓN 1: KPIs
    # =========================
    st.subheader("🔹 Indicadores generales")

    col1, col2, col3 = st.columns(3)

    # KPI 1: total de fallas (filtro actual)
    total_fallas = len(t1) if not t1.empty else 0

    # KPI 2: máquina con más fallas (global, sin filtros)
    if not tabla1.empty:
        serie_m = tabla1["Maquina"].dropna()
        serie_m = serie_m.astype(str).str.strip()
        mascara_validos = (serie_m != "") & (serie_m.str.upper() != "NAN")
        serie_m = serie_m[mascara_validos]

        conteo_global = serie_m.value_counts()

        if not conteo_global.empty:
            maq_top = conteo_global.idxmax()
            maq_top_ct = int(conteo_global.max())
            texto_maq_top = f"{maq_top} ({maq_top_ct})"
        else:
            texto_maq_top = "Sin datos"
    else:
        texto_maq_top = "Sin datos"

    # KPI 3: tiempo promedio entre fallas (filtro actual)
    prom_tiempo = (
        t2[COL_TIEMPO_ENTRE_FALLAS].mean()
        if not t2.empty else None
    )

    with col1:
        st.metric("Total de fallas (filtro actual)", total_fallas)

    with col2:
        st.metric("Máquina con más fallas (global)", texto_maq_top)

    with col3:
        if prom_tiempo is not None and pd.notna(prom_tiempo):
            st.metric("Tiempo promedio entre fallas", f"{prom_tiempo:.2f}")
        else:
            st.metric("Tiempo promedio entre fallas", "Sin datos")

    # ===== KPI extra: cluster categórico =====
    st.markdown("")
    col4, _ = st.columns(2)

    # Qué mostrar según selección de cluster/máquina
    if cluster_sel != "Todos":
        # Ya se está filtrando por ese cluster, así que lo mostramos directo
        cluster_cat = cluster_sel
    else:
        if maquina_sel == "Todas":
            cluster_cat = "Varios"
        else:
            if "Cluster" in t1.columns and not t1.empty:
                moda_cat = t1["Cluster"].astype(str).mode()
                cluster_cat = moda_cat.iloc[0] if not moda_cat.empty else "Sin datos"
            else:
                cluster_cat = "Sin datos"

    with col4:
        st.metric("Cluster categórico (filtro actual)", cluster_cat)

    st.markdown("---")

    # =========================
    # SECCIÓN 2: DISTRIBUCIONES
    # =========================
    st.subheader("🔹 Distribución de fallas por turno y EQ Type")

    col_a, col_b = st.columns(2)

    # --- Barras por turno ---
    with col_a:
        if "Turno" in t1.columns and not t1.empty:
            turno_counts = (
                t1["Turno"]
                .value_counts()
                .reset_index()
            )
            turno_counts.columns = ["Turno", "Fallas"]

            fig_turnos = px.bar(
                turno_counts,
                x="Turno",
                y="Fallas",
                text="Fallas",
                title="Fallas por turno",
                labels={"Turno": "Turno", "Fallas": "Número de fallas"},
                color_discrete_sequence=["#1f77b4"]  # azul fuerte
            )
            fig_turnos.update_traces(textposition="outside")
            fig_turnos.update_layout(uniformtext_minsize=8, uniformtext_mode="hide")
            st.plotly_chart(fig_turnos, use_container_width=True)
        else:
            st.info("No se encontró la columna de Turno o no hay datos en la Tabla 1 con el filtro actual.")

    # --- Barras por EQ Type (ubicación / tipo de equipo) ---
    with col_b:
        if "EQ_Type" in t1.columns and not t1.empty:
            ubic_counts = (
                t1["EQ_Type"]
                .value_counts()
                .reset_index()
            )
            ubic_counts.columns = ["EQ_Type", "Fallas"]

            fig_ubic = px.bar(
                ubic_counts,
                x="Fallas",
                y="EQ_Type",
                orientation="h",
                text="Fallas",
                title="Fallas por EQ Type",
                labels={"EQ_Type": "EQ Type / Tipo de equipo", "Fallas": "Número de fallas"},
                color_discrete_sequence=["#6baed6"]  # azul más claro
            )
            fig_ubic.update_traces(textposition="outside")
            fig_ubic.update_layout(uniformtext_minsize=8, uniformtext_mode="hide")
            st.plotly_chart(fig_ubic, use_container_width=True)
        else:
            st.info("No se encontró la columna EQ_Type o no hay datos en la Tabla 1 con el filtro actual.")

    st.markdown("---")

    # =========================
    # SECCIÓN 3: SERIE DE TIEMPO
    # =========================
    st.subheader("🔹 Tiempo entre fallas y predicciones (detalle por máquina / cluster)")

    # 👉 No mostrar la gráfica cuando se filtra solo por cluster (máquina = Todas)
    if cluster_sel != "Todos" and maquina_sel == "Todas":
        st.info("Selecciona una máquina específica para ver la serie de tiempo y las predicciones.")
    else:
        if t2.empty:
            st.warning("No hay datos de tiempo entre fallas para el filtro actual.")
        else:
            # Serie real
            serie_real = t2[[COL_IDX_TIEMPO, COL_TIEMPO_ENTRE_FALLAS]].copy()
            serie_real = serie_real.dropna(subset=[COL_TIEMPO_ENTRE_FALLAS])
            serie_real["Tipo"] = "Real"
            serie_real = serie_real.rename(columns={COL_TIEMPO_ENTRE_FALLAS: "Valor"})

            # Serie forecast (si hay datos para las mismas máquinas)
            if not t3.empty:
                serie_fore = t3[[COL_IDX_TIEMPO, COL_FORECAST]].copy()
                serie_fore = serie_fore.dropna(subset=[COL_FORECAST])
                serie_fore["Tipo"] = "Predicción"
                serie_fore = serie_fore.rename(columns={COL_FORECAST: "Valor"})

                serie_total = pd.concat([serie_real, serie_fore], ignore_index=True)
            else:
                serie_total = serie_real

            fig_serie = px.line(
                serie_total,
                x=COL_IDX_TIEMPO,
                y="Valor",
                color="Tipo",
                markers=True,
                title="Tiempo entre fallas (real vs predicción)",
                labels={COL_IDX_TIEMPO: "Índice de tiempo", "Valor": "Tiempo entre fallas"}
            )
            st.plotly_chart(fig_serie, use_container_width=True)

    st.markdown("---")

    # =========================
    # SECCIÓN 4: BOXPLOT (según filtro)
    # =========================
    st.subheader("🔹 Distribución del tiempo entre fallas por máquina (según filtro)")

    # 👀 Aquí usamos t2 (ya filtrado por cluster y/o máquina), NO tabla2
    if not t2.empty:
        box_data = t2[["Maquina", COL_TIEMPO_ENTRE_FALLAS]].dropna()

        fig_box = px.box(
            box_data,
            x="Maquina",
            y=COL_TIEMPO_ENTRE_FALLAS,
            title="Distribución del tiempo entre fallas por máquina (filtro actual)",
            labels={"Maquina": "Máquina", COL_TIEMPO_ENTRE_FALLAS: "Tiempo entre fallas"}
        )
        st.plotly_chart(fig_box, use_container_width=True)
    else:
        st.info("No hay datos suficientes con el filtro actual para generar el boxplot.")
# -----------------------------
# EJECUCIÓN
# -----------------------------
if __name__ == "__main__":
    main()
