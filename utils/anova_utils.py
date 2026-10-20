import json
import warnings
from itertools import combinations
from pathlib import Path
from typing import BinaryIO, TextIO

import numpy as np
import pandas as pd
from scipy.stats import studentized_range
from statsmodels.formula.api import ols
from statsmodels.regression.linear_model import RegressionResultsWrapper
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd


def cargar_datos(archivo: str | Path | BinaryIO | TextIO) -> pd.DataFrame:
    """Carga datos desde un archivo CSV o Excel.

    Args:
        archivo: Ruta o archivo binario/texto con extensión ``.csv`` o ``.xlsx``.

    Returns:
        Datos leídos en un DataFrame.

    Raises:
        ValueError: Si el archivo no tiene una extensión compatible.
    """
    # Se identifica la extensión para elegir el lector adecuado según el formato.
    nombre_archivo = (
        str(archivo)
        if isinstance(archivo, (str, Path))
        else getattr(archivo, "name", None)
    )
    if not isinstance(nombre_archivo, str):
        raise ValueError("El archivo debe tener un nombre con extensión .csv o .xlsx.")

    extension = Path(nombre_archivo).suffix.lower()
    # Excel se lee directamente; para CSV pandas detecta si el separador es coma o punto y coma.
    if extension == ".xlsx":
        return pd.read_excel(archivo)
    if extension == ".csv":
        return pd.read_csv(archivo, sep=None, engine="python")

    raise ValueError("Formato no compatible. Use un archivo .csv o .xlsx.")


def validar_dca(df: pd.DataFrame, col_trat: str, col_resp: str) -> list[str]:
    """Valida los datos requeridos para un diseño completamente al azar.

    Args:
        df: Datos que contienen tratamientos y respuesta.
        col_trat: Nombre de la columna de tratamientos.
        col_resp: Nombre de la columna de respuesta numérica.

    Returns:
        Mensajes de error en español; la lista queda vacía si los datos son válidos.
    """
    errores: list[str] = []
    # Se comprueba que existan las columnas antes de acceder a ellas.
    faltantes = [
        col for col in dict.fromkeys((col_trat, col_resp)) if col not in df.columns
    ]
    if faltantes:
        errores.append(f"Faltan las columnas requeridas: {', '.join(faltantes)}.")
        return errores

    # Se evita asignar un mismo campo simultáneamente al tratamiento y a la respuesta.
    if col_trat == col_resp:
        errores.append("Las columnas de tratamiento y respuesta deben ser distintas.")

    # La respuesta debe ser numérica para que el modelo pueda estimar medias y variación.
    if not pd.api.types.is_numeric_dtype(df[col_resp]):
        errores.append(f"La columna de respuesta '{col_resp}' debe ser numérica.")

    # Se detectan datos faltantes en las variables que intervienen en el análisis.
    if df[[col_trat, col_resp]].isna().any().any():
        errores.append("Hay datos faltantes en las columnas de tratamiento o respuesta.")

    # Se cuenta cada tratamiento observado y sus réplicas para verificar la replicación mínima.
    conteos = df.groupby(col_trat, observed=True, dropna=True).size()
    if len(conteos) < 2:
        errores.append("Se requieren al menos dos tratamientos.")
    if (conteos < 2).any():
        errores.append("Cada tratamiento debe tener al menos dos réplicas.")

    return errores


def ajustar_dca(
    df: pd.DataFrame, col_trat: str, col_resp: str
) -> RegressionResultsWrapper:
    """Ajusta un modelo ANOVA de un factor para un DCA.

    Args:
        df: Datos del ensayo.
        col_trat: Nombre de la columna de tratamientos.
        col_resp: Nombre de la columna de respuesta.

    Returns:
        Modelo lineal ajustado por mínimos cuadrados ordinarios.

    Raises:
        ValueError: Si los datos no cumplen los requisitos mínimos del DCA.
    """
    # Se detiene el ajuste si el número de tratamientos o réplicas no es válido.
    errores = validar_dca(df, col_trat, col_resp)
    if errores:
        raise ValueError("No se puede ajustar el DCA: " + " ".join(errores))

    # Q protege nombres de columnas con espacios o caracteres especiales en la fórmula.
    formula = f"Q({json.dumps(col_resp)}) ~ C(Q({json.dumps(col_trat)}))"
    # OLS estima las medias de tratamientos y el error residual para la comparación.
    return ols(formula, data=df).fit()


def tabla_anova(modelo: RegressionResultsWrapper) -> pd.DataFrame:
    """Calcula la tabla ANOVA tipo II y agrega la suma total.

    Args:
        modelo: Modelo OLS ajustado para un DCA.

    Returns:
        Tabla ANOVA con fuentes y encabezados en español.
    """
    # La ANOVA tipo II separa la variación de tratamientos del error residual.
    anova = anova_lm(modelo, typ=2)
    filas: list[dict[str, float | str]] = []

    # El cuadrado medio divide la suma de cuadrados por sus grados: CM = SC / gl.
    for fuente_original, fila in anova.iterrows():
        es_error = "residual" in str(fuente_original).lower()
        suma_cuadrados = float(fila["sum_sq"])
        grados_libertad = float(fila["df"])
        filas.append(
            {
                "Fuente": "Error" if es_error else "Tratamientos",
                "gl": grados_libertad,
                "SC": suma_cuadrados,
                "CM": suma_cuadrados / grados_libertad,
                "F": float(fila["F"]) if pd.notna(fila["F"]) else np.nan,
                "p-valor": (
                    float(fila["PR(>F)"])
                    if pd.notna(fila["PR(>F)"])
                    else np.nan
                ),
            }
        )

    # La fila Total resume la variación observada: SC Total = suma(SC) y gl Total = n - 1.
    suma_total = float(anova["sum_sq"].sum())
    grados_totales = int(modelo.nobs) - 1
    filas.append(
        {
            "Fuente": "Total",
            "gl": float(grados_totales),
            "SC": suma_total,
            "CM": suma_total / grados_totales,
            "F": np.nan,
            "p-valor": np.nan,
        }
    )
    columnas = ["Fuente", "gl", "SC", "CM", "F", "p-valor"]
    return pd.DataFrame(filas, columns=columnas)


def resumen_tratamientos(
    df: pd.DataFrame, col_trat: str, col_resp: str
) -> pd.DataFrame:
    """Resume cantidad, total, media y desviación de la respuesta por tratamiento.

    Args:
        df: Datos del ensayo.
        col_trat: Nombre de la columna de tratamientos.
        col_resp: Nombre de la columna de respuesta.

    Returns:
        Estadísticos descriptivos ordenados por tratamiento.

    Raises:
        ValueError: Si los datos no cumplen los requisitos mínimos del DCA.
    """
    # Se evita resumir si faltan tratamientos o réplicas requeridas.
    errores = validar_dca(df, col_trat, col_resp)
    if errores:
        raise ValueError("No se puede resumir el DCA: " + " ".join(errores))

    # Se calcula n, total, media y desviación muestral (ddof = 1) por tratamiento.
    resumen = (
        df.groupby(col_trat, observed=True)[col_resp]
        .agg(
            n="count",
            total="sum",
            media="mean",
            desviacion_estandar="std",
        )
        .reset_index()
        .rename(columns={"desviacion_estandar": "desviación estándar"})
    )
    return resumen


def coeficiente_variacion(
    modelo: RegressionResultsWrapper, df: pd.DataFrame, col_resp: str
) -> float:
    """Calcula el coeficiente de variación del ensayo.

    Args:
        modelo: Modelo OLS ajustado para el DCA.
        df: Datos del ensayo.
        col_resp: Nombre de la columna de respuesta.

    Returns:
        Coeficiente de variación expresado como porcentaje.

    Raises:
        ValueError: Si falta la columna o la media general es cero/no numérica.
    """
    # Se valida la respuesta antes de obtener la media general del ensayo.
    if col_resp not in df.columns or not pd.api.types.is_numeric_dtype(df[col_resp]):
        raise ValueError(
            f"La columna de respuesta '{col_resp}' debe existir y ser numérica."
        )
    media_general = float(df[col_resp].mean())
    if not np.isfinite(media_general) or media_general == 0:
        raise ValueError(
            "La media general debe ser finita y distinta de cero para calcular el CV."
        )

    # La raíz del CME es el error típico; CV = sqrt(CME) / media general * 100.
    return float(np.sqrt(modelo.mse_resid) / media_general * 100)


def tukey(
    df: pd.DataFrame, col_trat: str, col_resp: str, alfa: float = 0.05
) -> tuple[pd.DataFrame, float]:
    """Compara medias con Tukey y calcula la diferencia mínima significativa.

    Args:
        df: Datos del ensayo.
        col_trat: Nombre de la columna de tratamientos.
        col_resp: Nombre de la columna de respuesta.
        alfa: Nivel de significancia entre 0 y 1.

    Returns:
        Una tabla de comparaciones de Tukey en español y la DMS.

    Raises:
        ValueError: Si alfa o los datos del DCA no son válidos.
    """
    # Se restringe alfa al intervalo válido para niveles de significancia.
    if not np.isfinite(alfa) or not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe ser un número entre 0 y 1.")

    # Se valida el diseño antes de estimar comparaciones entre medias.
    errores = validar_dca(df, col_trat, col_resp)
    if errores:
        raise ValueError("No se puede aplicar Tukey: " + " ".join(errores))

    # Tukey controla el error familiar al comparar todas las parejas de tratamientos.
    resultado = pairwise_tukeyhsd(
        endog=df[col_resp], groups=df[col_trat], alpha=alfa
    )
    # Los pares se enumeran en el mismo orden que las diferencias calculadas por Tukey.
    pares = list(combinations(resultado.groupsunique.tolist(), 2))
    comparaciones = pd.DataFrame(
        {
            "Tratamiento 1": [par[0] for par in pares],
            "Tratamiento 2": [par[1] for par in pares],
            "Diferencia de medias": resultado.meandiffs,
            "p-valor ajustado": resultado.pvalues,
            "Límite inferior": resultado.confint[:, 0],
            "Límite superior": resultado.confint[:, 1],
            "Rechaza H0": resultado.reject,
        }
    )
    # El CME y gl del error provienen de la ANOVA del mismo diseño.
    modelo = ajustar_dca(df, col_trat, col_resp)
    anova = tabla_anova(modelo)
    fila_error = anova.loc[anova["Fuente"] == "Error"].iloc[0]
    cme = float(fila_error["CM"])
    gl_error = float(fila_error["gl"])
    conteos = df.groupby(col_trat, observed=True).size()
    cantidad_tratamientos = len(conteos)
    balanceado = bool(conteos.nunique() == 1)

    # Con réplicas desiguales se usa su media armónica en DMS = q * sqrt(CME / r).
    if balanceado:
        replicas = float(conteos.iloc[0])
    else:
        warnings.warn(
            "El diseño no está balanceado; la DMS calculada con la media armónica "
            "de réplicas es aproximada.",
            UserWarning,
            stacklevel=2,
        )
        replicas = float(cantidad_tratamientos / (1 / conteos).sum())

    # El cuantil q usa k tratamientos y los grados de libertad del error.
    cuantil = float(
        studentized_range.ppf(1 - alfa, cantidad_tratamientos, gl_error)
    )
    # DMS = q(alfa; k; glE) * sqrt(CME / r) establece la diferencia crítica entre medias.
    dms = float(cuantil * np.sqrt(cme / replicas))
    return comparaciones, dms


def interpretar_dca(tabla: pd.DataFrame, alfa: float = 0.05) -> str:
    """Interpreta la prueba F de tratamientos en una tabla ANOVA.

    Args:
        tabla: Tabla generada por ``tabla_anova``.
        alfa: Nivel de significancia entre 0 y 1.

    Returns:
        Explicación sencilla de la decisión estadística y su significado práctico.

    Raises:
        ValueError: Si alfa o la fila de tratamientos no son válidos.
    """
    # Se comprueba alfa para que la decisión use un nivel de significancia definido.
    if not np.isfinite(alfa) or not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe ser un número entre 0 y 1.")
    if "Fuente" not in tabla.columns or "p-valor" not in tabla.columns:
        raise ValueError("La tabla debe incluir las columnas 'Fuente' y 'p-valor'.")

    # Se recupera el p-valor del contraste global, que evalúa H0: todas las medias son iguales.
    filas_tratamientos = tabla.loc[tabla["Fuente"] == "Tratamientos", "p-valor"]
    if filas_tratamientos.empty or pd.isna(filas_tratamientos.iloc[0]):
        raise ValueError("La tabla debe contener un p-valor válido para Tratamientos.")
    p_valor = float(filas_tratamientos.iloc[0])

    # Se compara p con alfa para decidir si hay evidencia de diferencias en las medias.
    if p_valor < alfa:
        return (
            f"Se rechaza H0 (p-valor = {p_valor:.4g} < alfa = {alfa:g}). "
            "Hay evidencia de que al menos un tratamiento tiene una media diferente; "
            "la decisión debe considerar cuáles tratamientos difieren y su relevancia agrícola."
        )
    return (
        f"No se rechaza H0 (p-valor = {p_valor:.4g} ≥ alfa = {alfa:g}). "
        "No hay evidencia suficiente para afirmar que las medias de los tratamientos difieren; "
        "esto no demuestra que sean idénticas."
    )
