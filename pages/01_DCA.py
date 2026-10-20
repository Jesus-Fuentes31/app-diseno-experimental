from io import BytesIO
from pathlib import Path

import plotly.express as px
import pandas as pd
import streamlit as st
from scipy.stats import f as distribucion_f

from utils.anova_utils import (
    ajustar_dca,
    cargar_datos,
    coeficiente_variacion,
    interpretar_dca,
    resumen_tratamientos,
    tabla_anova,
    tukey,
    validar_dca,
)
from utils.diagnostico_utils import (
    grafico_qq,
    grafico_residuos_vs_ajustados,
    prueba_levene,
    prueba_shapiro,
    residuos_y_ajustados,
)


@st.cache_data
def cargar_datos_cacheados(
    contenido: bytes | None, nombre_archivo: str
) -> pd.DataFrame:
    """Carga en caché los datos de ejemplo o el archivo seleccionado.

    Args:
        contenido: Bytes del archivo cargado, o ``None`` para usar el ejemplo.
        nombre_archivo: Nombre o ruta del archivo que leerá la función auxiliar.

    Returns:
        Datos leídos en un DataFrame.
    """
    if contenido is None:
        return cargar_datos(nombre_archivo)

    archivo_en_memoria = BytesIO(contenido)
    archivo_en_memoria.name = nombre_archivo
    return cargar_datos(archivo_en_memoria)


st.title("Diseño completamente al azar (DCA)")
st.write(
    "El DCA compara tratamientos asignados al azar cuando las unidades "
    "experimentales son homogéneas. En este ejemplo se evalúa si cuatro "
    "secadores solares producen diferencias en la humedad final de la yuca."
)

ruta_ejemplo = Path(__file__).resolve().parents[1] / "data" / "dca_secadores.csv"
archivo_cargado = st.file_uploader(
    "Carga los datos del ensayo", type=["csv", "xlsx"]
)
if archivo_cargado is None:
    st.caption(
        "No se cargó un archivo; se utilizan los datos de ejemplo "
        "data/dca_secadores.csv."
    )
    datos = cargar_datos_cacheados(None, str(ruta_ejemplo))
else:
    datos = cargar_datos_cacheados(
        archivo_cargado.getvalue(), archivo_cargado.name
    )

columnas = datos.columns.tolist()
indice_tratamiento = columnas.index("secador") if "secador" in columnas else 0
columnas_numericas = [
    columna
    for columna in columnas
    if datos[columna].dtype.kind in "iuf"
]
indice_respuesta = (
    columnas.index("humedad")
    if "humedad" in columnas
    else columnas.index(columnas_numericas[0])
    if columnas_numericas
    else 0
)

columna_tratamiento = st.selectbox(
    "Columna de tratamiento",
    columnas,
    index=indice_tratamiento,
)
columna_respuesta = st.selectbox(
    "Columna de respuesta",
    columnas,
    index=indice_respuesta,
)
alfa = st.slider(
    "Nivel de significancia (α)",
    min_value=0.01,
    max_value=0.10,
    value=0.05,
    step=0.01,
    format="%.2f",
)

errores = validar_dca(datos, columna_tratamiento, columna_respuesta)
if errores:
    for error in errores:
        st.error(error)
    st.stop()

modelo = ajustar_dca(datos, columna_tratamiento, columna_respuesta)
anova = tabla_anova(modelo)
resumen = resumen_tratamientos(
    datos, columna_tratamiento, columna_respuesta
)
cv = coeficiente_variacion(modelo, datos, columna_respuesta)

p_valor_tratamientos = float(
    anova.loc[anova["Fuente"] == "Tratamientos", "p-valor"].iloc[0]
)
gl_tratamientos = float(
    anova.loc[anova["Fuente"] == "Tratamientos", "gl"].iloc[0]
)
gl_error = float(anova.loc[anova["Fuente"] == "Error", "gl"].iloc[0])
f_critica = float(
    distribucion_f.ppf(1 - alfa, gl_tratamientos, gl_error)
)

pestana_datos, pestana_anova, pestana_comparaciones, pestana_graficos, pestana_supuestos = st.tabs(
    ["Datos", "ANOVA", "Comparaciones", "Gráficos", "Supuestos"]
)

with pestana_datos:
    st.subheader("Datos del ensayo")
    st.dataframe(datos, width="stretch")
    st.subheader("Resumen por tratamiento")
    st.dataframe(resumen, width="stretch", hide_index=True)

with pestana_anova:
    st.subheader("Análisis de varianza")
    st.dataframe(
        anova.style.format(
            {
                "gl": "{:.4f}",
                "SC": "{:.4f}",
                "CM": "{:.4f}",
                "F": "{:.4f}",
                "p-valor": "{:.4f}",
            },
            na_rep="—",
        ),
        width="stretch",
        hide_index=True,
    )
    st.metric("F crítica", f"{f_critica:.4f}")
    st.metric("Coeficiente de variación (CV)", f"{cv:.4f} %")
    interpretacion = interpretar_dca(anova, alfa)
    if p_valor_tratamientos < alfa:
        st.success(interpretacion)
    else:
        st.info(interpretacion)

with pestana_comparaciones:
    st.subheader("Comparaciones múltiples de Tukey")
    if p_valor_tratamientos < alfa:
        comparaciones, dms = tukey(
            datos, columna_tratamiento, columna_respuesta, alfa
        )
        st.dataframe(
            comparaciones.style.format(
                {
                    "Diferencia de medias": "{:.4f}",
                    "p-valor ajustado": "{:.4f}",
                    "Límite inferior": "{:.4f}",
                    "Límite superior": "{:.4f}",
                }
            ),
            width="stretch",
            hide_index=True,
        )
        st.metric("Diferencia mínima significativa (DMS)", f"{dms:.4f}")
    else:
        st.info(
            "No se realiza la prueba de Tukey porque el ANOVA no detectó "
            "diferencias estadísticamente significativas entre tratamientos "
            f"(p-valor = {p_valor_tratamientos:.4f} ≥ α = {alfa:.2f})."
        )

with pestana_graficos:
    st.subheader("Distribución de las respuestas")
    grafico_cajas = px.box(
        datos,
        x=columna_tratamiento,
        y=columna_respuesta,
        points="all",
        title="Respuesta por tratamiento",
        labels={
            columna_tratamiento: "Tratamiento",
            columna_respuesta: "Respuesta",
        },
    )
    st.plotly_chart(grafico_cajas, width="stretch")

    st.subheader("Medias por tratamiento")
    grafico_medias = px.bar(
        resumen,
        x=columna_tratamiento,
        y="media",
        error_y="desviación estándar",
        title="Media y desviación estándar por tratamiento",
        labels={
            columna_tratamiento: "Tratamiento",
            "media": "Media de la respuesta",
            "desviación estándar": "Desviación estándar",
        },
    )
    st.plotly_chart(grafico_medias, width="stretch")

with pestana_supuestos:
    st.subheader("Diagnóstico de supuestos del DCA")
    datos_residuos = residuos_y_ajustados(modelo)

    st.markdown(
        """
        - **Normalidad:** Shapiro-Wilk y el gráfico Q-Q evalúan si los residuos
          son compatibles con una distribución normal.
        - **Homogeneidad de varianzas:** Levene compara la variabilidad de la
          respuesta entre tratamientos; se centra en la mediana para mayor
          robustez ante desviaciones de normalidad.
        - **Independencia:** no se determina con estas pruebas. En el DCA se
          justifica principalmente mediante la asignación aleatoria de las
          unidades experimentales y una ejecución adecuada del ensayo.
        """
    )

    estadistico_shapiro, p_shapiro, conclusion_shapiro = prueba_shapiro(
        datos_residuos["Residuos"], alfa
    )
    estadistico_levene, p_levene, conclusion_levene = prueba_levene(
        datos, columna_tratamiento, columna_respuesta, alfa
    )
    tabla_supuestos = pd.DataFrame(
        [
            {
                "Prueba": "Shapiro-Wilk",
                "Estadístico": estadistico_shapiro,
                "p-valor": p_shapiro,
                "Conclusión": conclusion_shapiro,
            },
            {
                "Prueba": "Levene (mediana)",
                "Estadístico": estadistico_levene,
                "p-valor": p_levene,
                "Conclusión": conclusion_levene,
            },
        ]
    )
    st.dataframe(
        tabla_supuestos.style.format(
            {"Estadístico": "{:.4f}", "p-valor": "{:.4f}"}
        ),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Residuos vs. valores ajustados")
    st.plotly_chart(
        grafico_residuos_vs_ajustados(datos_residuos), width="stretch"
    )

    st.subheader("Gráfico Q-Q de los residuos")
    st.plotly_chart(
        grafico_qq(datos_residuos["Residuos"]), width="stretch"
    )
