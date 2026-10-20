import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import levene, probplot, shapiro
from statsmodels.regression.linear_model import RegressionResultsWrapper


def residuos_y_ajustados(modelo: RegressionResultsWrapper) -> pd.DataFrame:
    """Obtiene los residuos y valores ajustados de un modelo.

    Args:
        modelo: Modelo OLS ajustado para el diseño experimental.

    Returns:
        DataFrame con las columnas ``Ajustados`` y ``Residuos``.
    """
    # Los ajustados son las respuestas estimadas y los residuos = observado - ajustado.
    return pd.DataFrame(
        {"Ajustados": modelo.fittedvalues, "Residuos": modelo.resid}
    )


def prueba_shapiro(
    residuos: pd.Series | np.ndarray, alfa: float = 0.05
) -> tuple[float, float, str]:
    """Evalúa la normalidad de los residuos con Shapiro-Wilk.

    Args:
        residuos: Residuos del modelo ajustado.
        alfa: Nivel de significancia entre 0 y 1.

    Returns:
        Estadístico W, p-valor y conclusión en español.

    Raises:
        ValueError: Si alfa o el número de residuos no son válidos.
    """
    valores = np.asarray(residuos, dtype=float)
    if not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe ser un número entre 0 y 1.")
    if valores.ndim != 1 or len(valores) < 3 or not np.isfinite(valores).all():
        raise ValueError("Shapiro-Wilk requiere al menos tres residuos finitos.")

    # Shapiro-Wilk contrasta si los residuos provienen de una distribución normal.
    estadistico, p_valor = shapiro(valores)
    if p_valor < alfa:
        conclusion = (
            "Se rechaza la normalidad: hay evidencia de que los residuos "
            "no siguen una distribución normal."
        )
    else:
        conclusion = (
            "No se rechaza la normalidad: no hay evidencia suficiente para "
            "afirmar que los residuos se apartan de una distribución normal."
        )
    return float(estadistico), float(p_valor), conclusion


def prueba_levene(
    df: pd.DataFrame,
    col_trat: str,
    col_resp: str,
    alfa: float = 0.05,
) -> tuple[float, float, str]:
    """Evalúa la igualdad de varianzas entre tratamientos con Levene.

    Args:
        df: Datos del ensayo con tratamiento y respuesta.
        col_trat: Nombre de la columna de tratamientos.
        col_resp: Nombre de la columna de respuesta numérica.
        alfa: Nivel de significancia entre 0 y 1.

    Returns:
        Estadístico W, p-valor y conclusión en español.

    Raises:
        ValueError: Si faltan columnas, hay datos inválidos o menos de dos grupos.
    """
    if not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe ser un número entre 0 y 1.")
    faltantes = [col for col in (col_trat, col_resp) if col not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan las columnas requeridas: {', '.join(faltantes)}.")
    if not pd.api.types.is_numeric_dtype(df[col_resp]):
        raise ValueError(f"La columna de respuesta '{col_resp}' debe ser numérica.")
    if df[[col_trat, col_resp]].isna().any().any():
        raise ValueError("Levene no puede calcularse si hay datos faltantes.")

    # Se preparan los valores de respuesta separados por tratamiento para comparar sus dispersiones.
    grupos = [
        grupo[col_resp].to_numpy(dtype=float)
        for _, grupo in df.groupby(col_trat, observed=True, sort=False)
    ]
    if len(grupos) < 2 or any(len(grupo) < 2 for grupo in grupos):
        raise ValueError(
            "Levene requiere al menos dos tratamientos con dos observaciones cada uno."
        )
    if not all(np.isfinite(grupo).all() for grupo in grupos):
        raise ValueError("Levene requiere respuestas numéricas finitas.")

    # Levene con center='median' es robusta cuando las distribuciones no son perfectamente normales.
    estadistico, p_valor = levene(*grupos, center="median")
    if p_valor < alfa:
        conclusion = (
            "Se rechaza la igualdad de varianzas: hay evidencia de variabilidad "
            "diferente entre tratamientos."
        )
    else:
        conclusion = (
            "No se rechaza la igualdad de varianzas: no hay evidencia suficiente "
            "de variabilidad diferente entre tratamientos."
        )
    return float(estadistico), float(p_valor), conclusion


def grafico_residuos_vs_ajustados(datos_residuos: pd.DataFrame) -> go.Figure:
    """Crea el gráfico de residuos contra valores ajustados.

    Args:
        datos_residuos: DataFrame producido por ``residuos_y_ajustados``.

    Returns:
        Gráfico interactivo de dispersión con referencia en cero.

    Raises:
        ValueError: Si faltan las columnas requeridas.
    """
    requeridas = {"Ajustados", "Residuos"}
    if not requeridas.issubset(datos_residuos.columns):
        raise ValueError("Se requieren las columnas 'Ajustados' y 'Residuos'.")

    # El patrón aleatorio alrededor de cero permite inspeccionar forma y dispersión del error.
    figura = px.scatter(
        datos_residuos,
        x="Ajustados",
        y="Residuos",
        title="Residuos vs. valores ajustados",
        labels={"Ajustados": "Valores ajustados", "Residuos": "Residuos"},
    )
    figura.add_hline(y=0, line_dash="dash", line_color="red")
    return figura


def grafico_qq(residuos: pd.Series | np.ndarray) -> go.Figure:
    """Crea un gráfico Q-Q para comparar residuos con la normal teórica.

    Args:
        residuos: Residuos del modelo ajustado.

    Returns:
        Gráfico interactivo de cuantiles observados contra cuantiles teóricos.

    Raises:
        ValueError: Si hay menos de tres residuos finitos.
    """
    valores = np.asarray(residuos, dtype=float)
    if valores.ndim != 1 or len(valores) < 3 or not np.isfinite(valores).all():
        raise ValueError("El gráfico Q-Q requiere al menos tres residuos finitos.")

    # probplot ordena los residuos y calcula cuantiles normales para inspeccionar su normalidad.
    (cuantiles_teoricos, cuantiles_observados), (pendiente, intercepto, _) = (
        probplot(valores, dist="norm")
    )
    figura = px.scatter(
        x=cuantiles_teoricos,
        y=cuantiles_observados,
        title="Gráfico Q-Q de los residuos",
        labels={
            "x": "Cuantiles teóricos normales",
            "y": "Cuantiles observados de residuos",
        },
    )
    # La recta de referencia muestra el patrón esperado si los residuos son aproximadamente normales.
    figura.add_trace(
        go.Scatter(
            x=cuantiles_teoricos,
            y=pendiente * cuantiles_teoricos + intercepto,
            mode="lines",
            name="Referencia normal",
        )
    )
    return figura
