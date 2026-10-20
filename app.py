import streamlit as st


AUTOR = "Jesus Fuentes"

st.set_page_config(
    page_title="App de Diseño Experimental",
    page_icon="🌱",
    layout="wide",
)

st.title("Aplicación de Diseño Experimental")
st.subheader("Ingeniería Agrícola – Universidad de Sucre")
st.write(
    "El diseño experimental permite planear ensayos de campo para comparar "
    "tratamientos de manera ordenada y confiable. Al controlar las fuentes de "
    "variación y organizar la toma de datos, ayuda a evaluar prácticas y "
    "tecnologías agrícolas y a sustentar decisiones con evidencia."
)

st.header("Módulos disponibles")
modulos = [
    {
        "Módulo": "DCA — Diseño completamente al azar",
        "Cuándo se usa": "Cuando las unidades experimentales son homogéneas y los tratamientos se asignan al azar.",
        "Ejemplo agrícola": "Comparar cuatro secadores para evaluar la humedad final de la yuca.",
        "Estado": "Disponible",
    },
    {
        "Módulo": "DBCA — Diseño de bloques completos al azar",
        "Cuándo se usa": "Cuando existe una fuente conocida de variación que se puede agrupar en bloques.",
        "Ejemplo agrícola": "Comparar fertilizantes agrupando parcelas por el gradiente de fertilidad del suelo.",
        "Estado": "En construcción",
    },
    {
        "Módulo": "DCL — Diseño de cuadrado latino",
        "Cuándo se usa": "Cuando se deben controlar dos fuentes de variación mediante filas y columnas.",
        "Ejemplo agrícola": "Evaluar variedades de maíz controlando gradientes de suelo en dos direcciones.",
        "Estado": "En construcción",
    },
    {
        "Módulo": "DPD — Diseño de parcelas divididas",
        "Cuándo se usa": "Cuando dos factores se aplican en unidades experimentales de distinto tamaño.",
        "Ejemplo agrícola": "Evaluar sistemas de riego en parcelas grandes y dosis de fertilizante en subparcelas.",
        "Estado": "En construcción",
    },
    {
        "Módulo": "Factoriales",
        "Cuándo se usa": "Cuando se estudian simultáneamente varios factores y sus posibles interacciones.",
        "Ejemplo agrícola": "Evaluar combinaciones de variedades y dosis de nitrógeno en el rendimiento del arroz.",
        "Estado": "En construcción",
    },
    {
        "Módulo": "RSM — Metodología de superficie de respuesta",
        "Cuándo se usa": "Cuando se busca modelar y optimizar una respuesta en función de factores cuantitativos.",
        "Ejemplo agrícola": "Optimizar temperatura y tiempo de secado para reducir la humedad de un grano.",
        "Estado": "En construcción",
    },
]
st.table(modulos)

st.header("Instrucciones de uso")
st.markdown(
    """
1. Elige el módulo correspondiente al diseño de tu ensayo.
2. Carga los datos con las columnas que solicita el módulo.
3. Revisa los resultados y las gráficas generadas.
4. Verifica los cálculos a mano y sustenta tu interpretación.
"""
)

st.warning(
    "Esta app apoya el aprendizaje. El estudiante interpreta los resultados, "
    "verifica supuestos y compara con su cálculo manual."
)

with st.sidebar:
    st.header("Información del curso")
    st.write(f"**Autor:** {AUTOR}")
    st.write("**Curso:** Diseño Experimental")
    st.write("**Semestre:** 2026-2")
