# Instrucciones del proyecto

## Proyecto

Esta es una aplicación de Diseño Experimental desarrollada en Python y Streamlit para el curso de Diseño Experimental del programa de Ingeniería Agrícola de la Universidad de Sucre.

## Estructura

- `app.py`: portada de la aplicación.
- `pages/`: una página por cada diseño experimental.
- `utils/`: funciones reutilizables; debe incluir `__init__.py`.
- `data/`: archivos CSV de ejemplo.
- `verificacion/`: scripts de R para verificar los análisis.

## Idioma y documentación

- Escribe en español todo el código visible para las personas: comentarios, docstrings y mensajes de la interfaz.
- Añade un comentario en cada paso estadístico que explique qué calcula y por qué, con explicaciones apropiadas para estudiantes de Ingeniería Agrícola.
- Define las funciones con anotaciones de tipos (type hints) y docstrings en estilo Google.

## Librerías permitidas

Usa únicamente `streamlit`, `pandas`, `numpy`, `scipy`, `statsmodels`, `plotly` y `openpyxl`. No agregues otras dependencias sin pedir permiso.

## Análisis estadístico

- Ajusta los modelos ANOVA con `statsmodels.formula.api.ols`.
- Calcula las tablas ANOVA con `statsmodels.stats.anova.anova_lm`, usando `typ=2`.
- Realiza las comparaciones de Tukey con `statsmodels.stats.multicomp.pairwise_tukeyhsd`.
- No inventes ni codifiques resultados estadísticos: todos los números presentados deben provenir del cálculo correspondiente.

## Verificación

Antes de finalizar cada tarea, ejecuta el código pertinente y corrige los errores que aparezcan.
