"""
Dashboard Financiero Personal — Claudio Socias Paradiz v4
Cambios v4:
  - Sección 6: Flujo Financiero Madrid (Vecdis + Mediolanum)
  - KPIs Madrid con score financiero
  - Proyección ahorro acumulado 24 meses
  - Proyección inversión Mediolanum

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/dashboard_app.py
    Abre http://127.0.0.1:8050
"""
import os
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go

BASE_DIR = Path(__file__).parent.parent
DB_FILE = str(BASE_DIR / os.environ.get("DB_FILE", "finanzas.db"))

MESES_ES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
            7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

AZUL    = "#1B4F72"
AZUL_C  = "#2E86C1"
VERDE   = "#1E8449"
ROJO    = "#C0392B"
NARANJA = "#E67E22"
GRIS    = "#7F8C8D"
DORADO  = "#D4AC0D"
FONDO   = "#0D1B2A"
FONDO2  = "#162535"
FONDO3  = "#1A2F45"
TEXTO   = "#E8F4FD"
GRID    = "#1E3A52"
ACENTO  = "#3498DB"
PURPURA = "#8E44AD"

SALDO_CLP    = 6312618
CUOTA_CLP    = 283327
TASA_MENSUAL = 0.0116
TOTAL_CUOTAS = 35
CUOTA_ACTUAL = 9

trimestres = {"Q1":[1,2,3],"Q2":[4,5,6],"Q3":[7,8,9],"Q4":[10,11,12]}

SALDO_CAPITAL_CLP  = 6312618
CUOTA_MENSUAL_CLP  = 283327
LIQUIDACION_MES    = 12
LIQUIDACION_ANIO   = 2026

def get_conn():
    return sqlite3.connect(DB_FILE)

def lbl(anio, mes):
    return f"{MESES_ES[int(mes)]} {int(anio)}"

# ── Carga de datos ─────────────────────────────────────────────────────────────
def cargar_tipo_cambio():
    conn = get_conn()
    df = pd.read_sql(
        "SELECT anio, mes, clp_eur FROM tipo_cambio ORDER BY anio, mes", conn)
    conn.close()
    df["fecha"] = pd.to_datetime(df.apply(
        lambda r: f"{int(r.anio)}-{int(r.mes):02d}-01", axis=1))
    df["label"] = df.apply(lambda r: lbl(r.anio, r.mes), axis=1)
    return df

def cargar_ingresos():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT m.anio, m.mes, m.descripcion,
               ROUND(m.abono_clp / t.clp_eur, 0) as eur,
               m.abono_clp
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria = 'ingreso_laboral' AND m.abono_clp > 100
        ORDER BY m.anio, m.mes
    """, conn)
    conn.close()
    df["empresa"] = df["descripcion"].apply(
        lambda x: "PwC" if "PRICEWATERH" in x
        else "Por Cuenta Propia" if "Cuenta Propia" in x
        else "Clínica Arcaya")
    df["fecha"] = pd.to_datetime(df.apply(
        lambda r: f"{int(r.anio)}-{int(r.mes):02d}-01", axis=1))
    df["label"] = df.apply(lambda r: lbl(r.anio, r.mes), axis=1)
    return df

def cargar_gastos_mensuales():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT m.anio, m.mes,
          ROUND(SUM(CASE WHEN m.subcategoria != 'retiro_efectivo'
            THEN m.cargo_clp / t.clp_eur ELSE 0 END),0) as total_eur,
          ROUND(SUM(CASE WHEN m.subcategoria IN
            ('amort_deuda_tc','pago_minimo_tc','intereses','comision_banco')
            THEN m.cargo_clp / t.clp_eur ELSE 0 END),0) as deuda_eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.categoria_padre NOT IN ('ignorar','transferencias')
        AND m.cargo_clp > 0
        GROUP BY m.anio, m.mes ORDER BY m.anio, m.mes
    """, conn)
    conn.close()
    df["corriente_eur"] = df["total_eur"] - df["deuda_eur"]
    df["fecha"] = pd.to_datetime(df.apply(
        lambda r: f"{int(r.anio)}-{int(r.mes):02d}-01", axis=1))
    df["label"] = df.apply(lambda r: lbl(r.anio, r.mes), axis=1)
    return df

def cargar_deuda_mensual():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT m.anio, m.mes,
          ROUND(SUM(CASE WHEN m.subcategoria='amort_deuda_tc'
            THEN m.cargo_clp/t.clp_eur ELSE 0 END),0) as amort_deuda,
          ROUND(SUM(CASE WHEN m.subcategoria='pago_minimo_tc'
            THEN m.cargo_clp/t.clp_eur ELSE 0 END),0) as pago_minimo,
          ROUND(SUM(CASE WHEN m.subcategoria='intereses'
            THEN m.cargo_clp/t.clp_eur ELSE 0 END),0) as intereses,
          ROUND(SUM(CASE WHEN m.subcategoria='comision_banco'
            THEN m.cargo_clp/t.clp_eur ELSE 0 END),0) as comisiones
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria IN
          ('amort_deuda_tc','pago_minimo_tc','intereses','comision_banco')
        AND m.cargo_clp > 0
        GROUP BY m.anio, m.mes ORDER BY m.anio, m.mes
    """, conn)
    conn.close()
    df["total"] = df[["amort_deuda","pago_minimo","intereses","comisiones"]].sum(axis=1)
    tc_actual = 1070.0
    saldo_eur_actual = SALDO_CAPITAL_CLP / tc_actual
    cuota_eur = CUOTA_MENSUAL_CLP / tc_actual
    n = len(df)
    saldos = [0.0] * n
    saldos[-1] = saldo_eur_actual
    for i in range(n-2, -1, -1):
        saldos[i] = saldos[i+1] + df["amort_deuda"].iloc[i+1]
    df["saldo_pendiente"] = saldos
    df["fecha"] = pd.to_datetime(df.apply(
        lambda r: f"{int(r.anio)}-{int(r.mes):02d}-01", axis=1))
    df["label"] = df.apply(lambda r: lbl(r.anio, r.mes), axis=1)
    return df, saldo_eur_actual, cuota_eur

def cargar_gastos_categoria():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT m.anio, m.mes, m.categoria_padre, m.subcategoria,
               ROUND(SUM(m.cargo_clp / t.clp_eur), 0) as eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.categoria_padre NOT IN ('ignorar','transferencias','finanzas')
        AND m.subcategoria != 'retiro_efectivo'
        AND m.cargo_clp > 0
        GROUP BY m.anio, m.mes, m.categoria_padre, m.subcategoria
        ORDER BY m.anio, m.mes
    """, conn)
    conn.close()
    df["fecha"] = pd.to_datetime(df.apply(
        lambda r: f"{int(r.anio)}-{int(r.mes):02d}-01", axis=1))
    return df

def cargar_ipc():
    conn = get_conn()
    df_es = pd.read_sql("""
        SELECT anio, mes, ipc_variacion_anual as ipc
        FROM mercado_ipc WHERE pais='España' ORDER BY anio, mes
    """, conn)
    df_cl = pd.read_sql("""
        SELECT anio, mes, ipc_variacion_mensual as ipc
        FROM mercado_ipc WHERE pais='Chile' ORDER BY anio, mes
    """, conn)
    conn.close()
    return df_es, df_cl

def cargar_datos_avanzados():
    conn = get_conn()
    df_cc = pd.read_sql("""
        SELECT m.anio, m.mes,
               ROUND(SUM(m.cargo_clp / t.clp_eur), 0) as gastos_cc
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.categoria_padre NOT IN ('ignorar','transferencias')
        AND m.subcategoria != 'retiro_efectivo'
        AND m.cargo_clp > 0
        GROUP BY m.anio, m.mes ORDER BY m.anio, m.mes
    """, conn)
    df_tc_mes = pd.read_sql("""
        SELECT CAST(strftime('%Y', c.fecha) AS INT) as anio,
               CAST(strftime('%m', c.fecha) AS INT) as mes,
               ROUND(SUM(c.monto_clp / t.clp_eur), 0) as gastos_tc
        FROM tc_compras c
        JOIN tipo_cambio t
            ON CAST(strftime('%Y', c.fecha) AS INT) = t.anio
            AND CAST(strftime('%m', c.fecha) AS INT) = t.mes
        WHERE c.categoria_padre NOT IN ('ignorar','finanzas')
        AND c.monto_clp > 0
        GROUP BY CAST(strftime('%Y', c.fecha) AS INT),
                 CAST(strftime('%m', c.fecha) AS INT)
        ORDER BY anio, mes
    """, conn)
    df_ing_adv = pd.read_sql("""
        SELECT m.anio, m.mes,
               ROUND(SUM(m.abono_clp / t.clp_eur), 0) as ingresos
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria = 'ingreso_laboral'
        AND m.abono_clp > 100000
        GROUP BY m.anio, m.mes ORDER BY m.anio, m.mes
    """, conn)
    df_top10 = pd.read_sql("""
        SELECT m.descripcion, m.subcategoria, m.categoria_padre,
               COUNT(*) as n,
               ROUND(SUM(m.cargo_clp / t.clp_eur), 0) as total_eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.categoria_padre NOT IN ('ignorar','transferencias','finanzas')
        AND m.subcategoria != 'retiro_efectivo'
        AND m.cargo_clp > 0
        GROUP BY m.descripcion ORDER BY total_eur DESC LIMIT 10
    """, conn)
    df_top10['nombre'] = df_top10['descripcion'].str.replace(
        'Compra Nacional ', '').str.replace('Compra Internacional ', '')
    df_top10['nombre'] = df_top10['nombre'].str[:28]
    df_tc_cat = pd.read_sql("""
        SELECT c.subcategoria,
               ROUND(SUM(c.monto_clp / t.clp_eur), 0) as eur
        FROM tc_compras c
        JOIN tipo_cambio t
            ON CAST(strftime('%Y', c.fecha) AS INT) = t.anio
            AND CAST(strftime('%m', c.fecha) AS INT) = t.mes
        WHERE c.categoria_padre NOT IN ('ignorar','finanzas')
        AND c.monto_clp > 0
        GROUP BY c.subcategoria ORDER BY eur DESC LIMIT 10
    """, conn)
    conn.close()
    for df in [df_cc, df_tc_mes, df_ing_adv]:
        df['fecha'] = pd.to_datetime(df.apply(
            lambda r: f"{int(r.anio)}-{int(r.mes):02d}-01", axis=1))
        df['label'] = df.apply(lambda r: lbl(r.anio, r.mes), axis=1)
    return df_cc, df_tc_mes, df_ing_adv, df_top10, df_tc_cat

def cargar_datos_madrid():
    conn = get_conn()
    try:
        df_ing_mad = pd.read_sql("""
            SELECT fecha_inicio, empresa, cargo, bruto_anual_eur,
                   neto_mensual_eur, flex_comida_eur, flex_transporte_eur,
                   variable_anual_eur
            FROM ingresos_madrid
            ORDER BY fecha_inicio DESC LIMIT 1
        """, conn)
    except Exception:
        df_ing_mad = pd.DataFrame()
    try:
        df_gastos_mad = pd.read_sql("""
            SELECT concepto, importe_eur, fecha_inicio, fecha_fin
            FROM gastos_fijos_madrid
            ORDER BY importe_eur DESC
        """, conn)
    except Exception:
        df_gastos_mad = pd.DataFrame()
    try:
        df_inv = pd.read_sql("""
            SELECT fecha_inicio, instrumento, tipo, entidad,
                   capital_eur, aportacion_mensual_eur, tae
            FROM inversiones
            ORDER BY fecha_inicio
        """, conn)
    except Exception:
        df_inv = pd.DataFrame()
    conn.close()
    return df_ing_mad, df_gastos_mad, df_inv

df_cc_adv, df_tc_mes_adv, df_ing_adv, df_top10, df_tc_cat = cargar_datos_avanzados()

# Cargar todo
df_tc                          = cargar_tipo_cambio()
df_ing                         = cargar_ingresos()
df_gm                          = cargar_gastos_mensuales()
df_deuda, saldo_eur, cuota_eur = cargar_deuda_mensual()
df_cat                         = cargar_gastos_categoria()
df_ipc_es, df_ipc_cl           = cargar_ipc()
df_ing_mad, df_gastos_mad, df_inv = cargar_datos_madrid()
anios_disp = sorted(df_gm["anio"].unique().tolist())

# ── Helpers ────────────────────────────────────────────────────────────────────
def filtrar(df, anio, trim, mes):
    dff = df.copy()
    if anio != "todos":
        dff = dff[dff["anio"] == int(anio)]
    if trim != "todos":
        dff = dff[dff["mes"].isin(trimestres[trim])]
    if mes != "todos":
        dff = dff[dff["mes"] == int(mes)]
    return dff

def layout_base(fig, titulo="", height=350):
    fig.update_layout(
        title=dict(text=titulo,
                   font=dict(color=TEXTO, size=13, family="Georgia"), x=0.01),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=FONDO2,
        font=dict(color=TEXTO, size=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXTO, size=10)),
        margin=dict(t=45, b=50, l=55, r=20),
        xaxis=dict(gridcolor=GRID, linecolor=GRID,
                   tickfont=dict(size=9, color=TEXTO)),
        yaxis=dict(gridcolor=GRID, linecolor=GRID,
                   tickfont=dict(size=9, color=TEXTO)),
        height=height,
    )
    return fig

ESTILO_CARD = {
    "backgroundColor": FONDO2, "borderRadius": "12px",
    "padding": "20px", "marginBottom": "20px",
    "border": f"1px solid {GRID}",
    "boxShadow": "0 4px 15px rgba(0,0,0,0.3)",
}
ESTILO_TITULO = {
    "color": ACENTO, "fontFamily": "Georgia, serif",
    "fontSize": "12px", "fontWeight": "bold",
    "letterSpacing": "2px", "textTransform": "uppercase",
    "marginBottom": "4px", "marginTop": "0",
}
ESTILO_DIC = {"borderTop": f"1px solid {GRID}", "margin": "8px 0 16px 0"}

def kpi(titulo, valor, sub, color=ACENTO):
    return html.Div([
        html.P(titulo, style={"color":GRIS,"fontSize":"10px","margin":"0",
               "letterSpacing":"1px","textTransform":"uppercase"}),
        html.H3(valor, style={"color":color,"fontSize":"22px",
                "margin":"4px 0","fontFamily":"Georgia, serif"}),
        html.P(sub, style={"color":GRIS,"fontSize":"10px","margin":"0"}),
    ], style={"backgroundColor":FONDO3,"borderRadius":"8px","padding":"14px",
              "borderLeft":f"3px solid {color}","flex":"1","minWidth":"140px"})

# ── Layout ─────────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, title="Dashboard Financiero — Claudio Socias",
                suppress_callback_exceptions=True)
server = app.server
app.layout = html.Div([
    # Header
    html.Div([
        html.Div([
            html.H1("Dashboard Financiero Personal", style={
                "color":TEXTO,"fontFamily":"Georgia, serif",
                "fontSize":"26px","margin":"0","fontWeight":"bold"}),
            html.P("Claudio Socias Paradiz  ·  Data Analyst | BI  ·  Santiago → Madrid  ·  2023-2026",
                style={"color":GRIS,"fontSize":"12px","margin":"6px 0 0 0"}),
        ]),
        html.Div([
            html.P(f"Actualizado: {date.today().strftime('%d/%m/%Y')}",
                style={"color":GRIS,"fontSize":"11px","textAlign":"right","margin":"0"}),
            html.P("Santander Chile · Global66 · Santander España · INE · BCCh",
                style={"color":GRIS,"fontSize":"10px","textAlign":"right","margin":"2px 0 0 0"}),
        ]),
    ], style={"display":"flex","justifyContent":"space-between","alignItems":"center",
              "backgroundColor":FONDO2,"padding":"24px 32px",
              "borderBottom":f"2px solid {ACENTO}","marginBottom":"24px"}),

    # Filtros
    html.Div([
        html.P("FILTROS GLOBALES", style=ESTILO_TITULO),
        html.Hr(style=ESTILO_DIC),
        html.Div([
            html.Div([
                html.Label("Año", style={"color":GRIS,"fontSize":"11px"}),
                dcc.Dropdown(id="f-anio",
                    options=[{"label":"Todos","value":"todos"}] +
                            [{"label":str(a),"value":a} for a in anios_disp],
                    value="todos", clearable=False,
                    style={"backgroundColor":FONDO3,"color":FONDO}),
            ], style={"flex":"1","marginRight":"16px"}),
            html.Div([
                html.Label("Trimestre", style={"color":GRIS,"fontSize":"11px"}),
                dcc.Dropdown(id="f-trim",
                    options=[{"label":"Todos","value":"todos"}] +
                            [{"label":q,"value":q} for q in trimestres],
                    value="todos", clearable=False,
                    style={"backgroundColor":FONDO3,"color":FONDO}),
            ], style={"flex":"1","marginRight":"16px"}),
            html.Div([
                html.Label("Mes", style={"color":GRIS,"fontSize":"11px"}),
                dcc.Dropdown(id="f-mes",
                    options=[{"label":"Todos","value":"todos"}] +
                            [{"label":MESES_ES[m],"value":m} for m in range(1,13)],
                    value="todos", clearable=False,
                    style={"backgroundColor":FONDO3,"color":FONDO}),
            ], style={"flex":"1"}),
        ], style={"display":"flex","gap":"16px"}),
    ], style={**ESTILO_CARD,"margin":"0 24px 20px 24px"}),

    # KPIs Chile
    html.Div(id="kpis", style={"margin":"0 24px 20px 24px"}),

    # Sección 1
    html.Div([
        html.P("MERCADO CAMBIARIO E INGRESOS LABORALES", style=ESTILO_TITULO),
        html.Hr(style=ESTILO_DIC),
        html.Div([
            html.Div([dcc.Graph(id="g-tc",  config={"displayModeBar":False})],
                     style={"flex":"1","marginRight":"16px"}),
            html.Div([dcc.Graph(id="g-ing", config={"displayModeBar":False})],
                     style={"flex":"1"}),
        ], style={"display":"flex"}),
    ], style={**ESTILO_CARD,"margin":"0 24px 20px 24px"}),

    # Sección 2
    html.Div([
        html.P("EVOLUCIÓN DE GASTOS Y DEUDA", style=ESTILO_TITULO),
        html.Hr(style=ESTILO_DIC),
        html.Div([
            html.Div([dcc.Graph(id="g-gasto", config={"displayModeBar":False})],
                     style={"flex":"1","marginRight":"16px"}),
            html.Div([dcc.Graph(id="g-balance", config={"displayModeBar":False})],
                     style={"flex":"1"}),
        ], style={"display":"flex"}),
    ], style={**ESTILO_CARD,"margin":"0 24px 20px 24px"}),

    # Sección 3
    html.Div([
        html.P("DISTRIBUCIÓN DE GASTOS POR CATEGORÍA", style=ESTILO_TITULO),
        html.Hr(style=ESTILO_DIC),
        dcc.Graph(id="g-barras", config={"displayModeBar":False}),
    ], style={**ESTILO_CARD,"margin":"0 24px 20px 24px"}),

    # Sección 4
    html.Div([
        html.P("ANÁLISIS COMPARATIVO: CHILE vs ESPAÑA", style=ESTILO_TITULO),
        html.Hr(style=ESTILO_DIC),
        html.Div([
            html.Div([dcc.Graph(id="g-poder", config={"displayModeBar":False})],
                     style={"flex":"1","marginRight":"16px"}),
            html.Div([dcc.Graph(id="g-sal",   config={"displayModeBar":False})],
                     style={"flex":"1"}),
        ], style={"display":"flex"}),
    ], style={**ESTILO_CARD,"margin":"0 24px 20px 24px"}),

    # Sección 5: Análisis Financiero Avanzado
    html.Div([
        html.P("ANÁLISIS FINANCIERO AVANZADO", style=ESTILO_TITULO),
        html.Hr(style=ESTILO_DIC),
        html.Div([
            html.Div([dcc.Graph(id="g-adv-gastos", config={"displayModeBar":False})],
                     style={"flex":"1","marginRight":"16px"}),
            html.Div([dcc.Graph(id="g-adv-tc-cat", config={"displayModeBar":False})],
                     style={"flex":"1"}),
        ], style={"display":"flex"}),
        html.Div([
            html.Div([dcc.Graph(id="g-adv-ahorro", config={"displayModeBar":False})],
                     style={"flex":"1","marginRight":"16px"}),
            html.Div([dcc.Graph(id="g-adv-top10", config={"displayModeBar":False})],
                     style={"flex":"1"}),
        ], style={"display":"flex","marginTop":"16px"}),
        html.Div([
            dcc.Graph(id="g-adv-proyeccion", config={"displayModeBar":False}),
        ], style={"marginTop":"16px"}),
    ], style={**ESTILO_CARD,"margin":"0 24px 20px 24px"}),

    # Sección 6: Flujo Financiero Madrid
    html.Div([
        html.P("FLUJO FINANCIERO MADRID — VECDIS 2026", style=ESTILO_TITULO),
        html.Hr(style=ESTILO_DIC),
        html.Div(id="kpis-madrid", style={"marginBottom":"16px"}),
        html.Div([
            html.Div([dcc.Graph(id="g-mad-flujo", config={"displayModeBar":False})],
                     style={"flex":"1","marginRight":"16px"}),
            html.Div([dcc.Graph(id="g-mad-proyeccion", config={"displayModeBar":False})],
                     style={"flex":"1"}),
        ], style={"display":"flex"}),
        html.Div([
            dcc.Graph(id="g-mad-inversion", config={"displayModeBar":False}),
        ], style={"marginTop":"16px"}),
    ], style={**ESTILO_CARD,"margin":"0 24px 20px 24px"}),

    # Footer
    html.Div([
        html.P("Fuentes: Santander Chile · Global66 · Santander España · INE España · mindicador.cl (BCCh) · Glassdoor/LinkedIn 2026",
            style={"color":GRIS,"fontSize":"10px","textAlign":"center","margin":"0"}),
    ], style={"padding":"16px 24px","borderTop":f"1px solid {GRID}"}),

], style={"backgroundColor":FONDO,"minHeight":"100vh","fontFamily":"Arial, sans-serif"})


# ── Callbacks Chile ────────────────────────────────────────────────────────────
@callback(Output("kpis","children"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_kpis(anio, trim, mes):
    dff_i = filtrar(df_ing, anio, trim, mes)
    dff_g = filtrar(df_gm,  anio, trim, mes)
    dff_t = filtrar(df_tc,  anio, trim, mes)
    ti   = dff_i["eur"].sum()
    tg   = dff_g["total_eur"].sum()
    td   = dff_g["deuda_eur"].sum()
    tc_p = dff_t["clp_eur"].mean() if len(dff_t) else 0
    bal  = ti - tg
    hoy = date.today()
    meses_liq = max(0, (LIQUIDACION_ANIO - hoy.year)*12 +
                       (LIQUIDACION_MES - hoy.month))
    return html.Div([
        kpi("Ingresos laborales", f"€{ti:,.0f}", "en el período", VERDE),
        kpi("Gasto total",        f"€{tg:,.0f}", "en el período", AZUL_C),
        kpi("Costo deuda",        f"€{td:,.0f}", "amort. + intereses", ROJO),
        kpi("TC promedio",        f"${tc_p:,.0f}", "CLP por EUR", DORADO),
        kpi("Saldo deuda TC",     f"€{saldo_eur:,.0f}",
            f"Liquidación en {meses_liq} meses (dic 2026)", NARANJA),
        kpi("Balance estimado",
            f"€{bal:,.0f}" if bal >= 0 else f"-€{abs(bal):,.0f}",
            "ingresos − gastos", VERDE if bal >= 0 else ROJO),
    ], style={"display":"flex","gap":"12px","flexWrap":"wrap"})


@callback(Output("g-tc","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_tc(anio, trim, mes):
    dff = filtrar(df_tc, anio, trim, mes).sort_values("fecha")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dff["label"], y=dff["clp_eur"], mode="lines+markers",
        line=dict(color=AZUL_C, width=2), marker=dict(size=5),
        fill="tozeroy", fillcolor="rgba(46,134,193,0.12)", name="CLP/EUR",
        hovertemplate="<b>%{x}</b><br>1 EUR = $%{y:,.0f} CLP<extra></extra>",
    ))
    if len(dff) > 1:
        prom = dff["clp_eur"].mean()
        fig.add_hline(y=prom, line_dash="dash", line_color=GRIS, opacity=0.6,
                      annotation_text=f"Prom. ${prom:,.0f}",
                      annotation_font_color=GRIS)
    layout_base(fig, "📈 Tipo de Cambio CLP/EUR")
    fig.update_xaxes(tickangle=45)
    fig.update_yaxes(title_text="CLP por EUR")
    return fig


@callback(Output("g-ing","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_ing(anio, trim, mes):
    dff = filtrar(df_ing, anio, trim, mes)
    grp = dff.groupby(["label","empresa","fecha"])["eur"].sum().reset_index()
    if grp.empty:
        return layout_base(go.Figure(), "💼 Ingresos Laborales en EUR")
    piv = grp.pivot_table(index=["fecha","label"], columns="empresa",
                          values="eur", aggfunc="sum", fill_value=0
                         ).reset_index().sort_values("fecha")
    fig = go.Figure()
    for emp, color in [("PwC", AZUL), ("Clínica Arcaya", AZUL_C), ("Por Cuenta Propia", VERDE)]:
        if emp in piv.columns:
            fig.add_trace(go.Bar(
                x=piv["label"], y=piv[emp], name=emp, marker_color=color,
                hovertemplate=f"<b>%{{x}}</b><br>{emp}: €%{{y:,.0f}}<extra></extra>",
            ))
    cols = [c for c in ["PwC","Clínica Arcaya","Por Cuenta Propia"] if c in piv.columns]
    if cols and len(piv) > 2:
        total = piv[cols].sum(axis=1).values
        total_filtrado = total[total > 0]
        x_filtrado = np.arange(len(total_filtrado))
        coef = np.polyfit(x_filtrado, total_filtrado, 1)
        pend = coef[0]
        tend = np.polyval(coef, np.arange(len(total)))
        fig.add_trace(go.Scatter(
            x=piv["label"], y=tend, mode="lines",
            name=f"Tendencia ({'+' if pend>=0 else ''}€{pend:.0f}/mes)",
            line=dict(color=DORADO, width=2, dash="dash"),
        ))
    layout_base(fig, "💼 Ingresos Laborales en EUR")
    fig.update_layout(barmode="stack", yaxis_title="EUR / mes", xaxis_tickangle=45)
    return fig


@callback(Output("g-gasto","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_gasto(anio, trim, mes):
    dff = filtrar(df_gm, anio, trim, mes).sort_values("fecha")
    fig = go.Figure()
    if dff.empty:
        return layout_base(fig, "📊 Evolución Gasto Mensual")
    fig.add_trace(go.Bar(
        x=dff["label"], y=dff["corriente_eur"], name="Gasto corriente",
        marker_color=AZUL_C, opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Corriente: €%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=dff["label"], y=dff["deuda_eur"], name="Amort. Deuda TC",
        marker_color=ROJO, opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Deuda: €%{y:,.0f}<extra></extra>",
    ))
    if len(dff) > 2:
        x_n  = np.arange(len(dff))
        coef = np.polyfit(x_n, dff["corriente_eur"].values, 1)
        tend = np.polyval(coef, x_n)
        fig.add_trace(go.Scatter(
            x=dff["label"], y=tend, mode="lines", name="Tendencia gasto",
            line=dict(color=VERDE, width=2, dash="dot"),
        ))
    sueldo_vecdis = 1704 + 220 + 136 + 28.35
    fig.add_hline(y=sueldo_vecdis, line_dash="dash", line_color=DORADO, opacity=0.7,
                  annotation_text=f"Sueldo efectivo Vecdis €{sueldo_vecdis:,.0f}",
                  annotation_font_color=DORADO)
    layout_base(fig, "📊 Evolución Gasto Mensual")
    fig.update_layout(barmode="stack", yaxis_title="EUR / mes", xaxis_tickangle=45)
    return fig


@callback(Output("g-balance","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_balance(anio, trim, mes):
    dff_gm = filtrar(df_gm, anio, trim, mes).sort_values("fecha")
    conn = get_conn()
    df_abonos = pd.read_sql("""
        SELECT m.anio, m.mes,
               ROUND(SUM(m.abono_clp / t.clp_eur), 0) as eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.abono_clp > 0
        AND m.subcategoria NOT IN ('ignorar')
        GROUP BY m.anio, m.mes
        ORDER BY m.anio, m.mes
    """, conn)
    conn.close()
    df_abonos["fecha"] = pd.to_datetime(df_abonos.apply(
        lambda r: f"{int(r.anio)}-{int(r.mes):02d}-01", axis=1))
    df_abonos["label"] = df_abonos.apply(lambda r: lbl(r.anio, r.mes), axis=1)
    dff_abonos = filtrar(df_abonos, anio, trim, mes).sort_values("fecha")
    dff_abonos = dff_abonos[(dff_abonos["eur"] > 500) & (dff_abonos["eur"] < 5000)]
    if dff_abonos.empty:
        return layout_base(go.Figure(), "💰 Balance Mensual")
    merged = dff_abonos.merge(
        dff_gm[["fecha","corriente_eur","deuda_eur"]], on="fecha", how="left"
    ).fillna(0)
    merged["total_gastos"] = merged["corriente_eur"] + merged["deuda_eur"]
    merged["balance"] = merged["eur"] - merged["total_gastos"]
    colores = [VERDE if b >= 0 else ROJO for b in merged["balance"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=merged["label"], y=merged["balance"],
        marker_color=colores, name="Balance",
        hovertemplate="<b>%{x}</b><br>Balance: €%{y:,.0f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_color=TEXTO, line_width=1.5)
    if len(merged) > 2:
        prom = merged["balance"].mean()
        fig.add_hline(y=prom, line_dash="dot", line_color=DORADO, opacity=0.7,
                      annotation_text=f"Prom. €{prom:,.0f}",
                      annotation_font_color=DORADO)
    layout_base(fig, "💰 Balance Mensual (Ingresos − Gastos)")
    fig.update_layout(yaxis_title="EUR / mes", xaxis_tickangle=45, showlegend=False)
    return fig


@callback(Output("g-barras","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_barras(anio, trim, mes):
    dff = filtrar(df_cat, anio, trim, mes)
    if dff.empty:
        return layout_base(go.Figure(), "📊 Gastos por Categoría", height=420)
    grp_full = dff.groupby(["categoria_padre","subcategoria"])["eur"].sum().reset_index()
    grp_full = grp_full[grp_full["eur"] > 0]
    grp = (grp_full.sort_values("eur", ascending=False)
           .groupby("categoria_padre").head(2)
           .sort_values("eur", ascending=True))
    cat_colors = {
        "alimentacion": AZUL_C, "transporte": VERDE,
        "salud_deporte": NARANJA, "servicios": DORADO,
        "alojamiento": GRIS, "comercio": PURPURA,
    }
    fig = go.Figure()
    for cat in grp["categoria_padre"].unique():
        sub = grp[grp["categoria_padre"] == cat]
        fig.add_trace(go.Bar(
            y=sub["subcategoria"], x=sub["eur"], orientation="h",
            name=cat, marker_color=cat_colors.get(cat, GRIS),
            hovertemplate="<b>%{y}</b><br>€%{x:,.0f}<extra></extra>",
        ))
    layout_base(fig, "📊 Gastos por Subcategoría (EUR total período)", height=500)
    fig.update_layout(
        barmode="group", xaxis_title="EUR", yaxis_title="",
        yaxis=dict(tickfont=dict(size=10, color=TEXTO)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


@callback(Output("g-poder","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_poder(anio, trim, mes):
    if anio != "todos":
        ipc_cl = df_ipc_cl[df_ipc_cl["anio"] == int(anio)]["ipc"].sum() / 100
    else:
        ipc_cl = df_ipc_cl["ipc"].sum() / 100
    ipc_es = df_ipc_es["ipc"].mean() / 100 if len(df_ipc_es) > 0 else 0.03
    cats       = ["Supermercado","Restaurantes","Taxi/Uber","Transporte","Gimnasio","Suscripciones","Alquiler"]
    base_chile = [272, 146, 25, 34, 41, 4, 865]
    base_mad   = [250, 80,  25, 50, 67, 55, 865]
    chile_aj   = [round(v*(1+ipc_cl)) for v in base_chile]
    madrid_aj  = [round(v*(1+ipc_es)) for v in base_mad]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Las Condes (aj. IPC)", x=cats, y=chile_aj,
        marker_color=AZUL, opacity=0.9,
        hovertemplate="<b>%{x}</b><br>Las Condes: €%{y:,.0f}/mes<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Chamberí (aj. IPC)", x=cats, y=madrid_aj,
        marker_color=NARANJA, opacity=0.9,
        hovertemplate="<b>%{x}</b><br>Chamberí: €%{y:,.0f}/mes<extra></extra>",
    ))
    layout_base(fig, "🏠 Poder Adquisitivo: Las Condes vs Chamberí")
    fig.update_layout(
        barmode="group", yaxis_title="EUR / mes",
        annotations=[dict(x=0.5, y=1.1, xref="paper", yref="paper",
            text=f"Ajustado IPC · Chile +{ipc_cl*100:.1f}% · España +{ipc_es*100:.1f}%",
            showarrow=False, font=dict(color=GRIS, size=10))],
    )
    return fig


@callback(Output("g-sal","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_salarial(anio, trim, mes):
    if anio != "todos":
        ipc_cl = df_ipc_cl[df_ipc_cl["anio"] == int(anio)]["ipc"].sum() / 100
    else:
        ipc_cl = df_ipc_cl["ipc"].sum() / 100
    ipc_es = df_ipc_es["ipc"].mean() / 100 if len(df_ipc_es) > 0 else 0.03
    sueldo_base = 1484 * 12 * (1 + ipc_cl)
    sueldo_ger  = 3007 * 12 * (1 + ipc_cl)
    niveles = ["Junior\n<3 años", "Mid-Senior\n3-5 años", "Senior\n+5 años ★", "Senior+\nPython"]
    sal_min = [round(v*(1+ipc_es)) for v in [22000,30000,38000,46000]]
    sal_max = [round(v*(1+ipc_es)) for v in [28000,38000,46000,55000]]
    colores = [GRIS, AZUL_C, VERDE, DORADO]
    fig = go.Figure()
    for i, (nivel, smin, smax, color) in enumerate(zip(niveles, sal_min, sal_max, colores)):
        fig.add_trace(go.Bar(
            x=[nivel], y=[smax-smin], base=[smin],
            marker_color=color, opacity=0.25, showlegend=False,
            hovertemplate=f"<b>{nivel}</b><br>€{smin:,}-€{smax:,}/año<extra></extra>",
        ))
        medio = (smin+smax)//2
        fig.add_trace(go.Scatter(
            x=[nivel], y=[medio], mode="markers+text",
            marker=dict(size=14, color=color, symbol="star" if i==2 else "circle"),
            text=[f"€{medio:,}"], textposition="top center",
            textfont=dict(color=color, size=10), showlegend=False,
            hovertemplate=f"<b>{nivel}</b><br>€{smin:,}-€{smax:,}/año<extra></extra>",
        ))
    fig.add_hline(y=sueldo_base, line_dash="dash", line_color=ROJO, opacity=0.8,
                  annotation_text=f"Sueldo base Chile €{sueldo_base:,.0f}/año",
                  annotation_font_color=ROJO, annotation_position="bottom right")
    fig.add_hline(y=sueldo_ger, line_dash="dot", line_color=NARANJA, opacity=0.8,
                  annotation_text=f"Gerente Arcaya €{sueldo_ger:,.0f}/año",
                  annotation_font_color=NARANJA, annotation_position="top right")
    layout_base(fig, "🌍 Comparación Salarial: Chile vs Madrid")
    fig.update_layout(
        yaxis_title="EUR / año bruto",
        annotations=list(fig.layout.annotations) + [dict(
            x=0.5, y=1.1, xref="paper", yref="paper",
            text=f"Aj. IPC · Chile +{ipc_cl*100:.1f}% · España +{ipc_es*100:.1f}% · ★ Tu perfil",
            showarrow=False, font=dict(color=GRIS, size=10))],
    )
    return fig


# ── Callbacks sección avanzada ─────────────────────────────────────────────────
@callback(Output("g-adv-gastos","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_adv_gastos(anio, trim, mes):
    dff_cc  = filtrar(df_cc_adv,     anio, trim, mes).sort_values("fecha")
    dff_tc  = filtrar(df_tc_mes_adv, anio, trim, mes).sort_values("fecha")
    dff_ing = filtrar(df_ing_adv,    anio, trim, mes).sort_values("fecha")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dff_cc["label"], y=dff_cc["gastos_cc"],
        name="Gastos CC", marker_color=AZUL_C, opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Gastos CC: €%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(x=dff_tc["label"], y=dff_tc["gastos_tc"],
        name="Gastos TC", marker_color=NARANJA, opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Gastos TC: €%{y:,.0f}<extra></extra>"))
    if not dff_ing.empty:
        fig.add_trace(go.Scatter(x=dff_ing["label"], y=dff_ing["ingresos"],
            mode="lines+markers", name="Ingresos", line=dict(color=VERDE, width=2),
            hovertemplate="<b>%{x}</b><br>Ingresos: €%{y:,.0f}<extra></extra>"))
    layout_base(fig, "📊 Gastos Mensuales CC + TC vs Ingresos")
    fig.update_layout(barmode="group", yaxis_title="EUR / mes", xaxis_tickangle=45)
    return fig


@callback(Output("g-adv-tc-cat","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_adv_tc_cat(anio, trim, mes):
    df = df_tc_cat.copy().sort_values("eur")
    cat_colors = {"seguro_salud":ROJO,"restaurante":AZUL_C,"plataforma_pago":GRIS,
                  "supermercado":VERDE,"kinesiologia":NARANJA,"delivery":DORADO}
    colores = [cat_colors.get(s, ACENTO) for s in df["subcategoria"]]
    fig = go.Figure(go.Bar(x=df["eur"], y=df["subcategoria"], orientation="h",
        marker_color=colores, hovertemplate="<b>%{y}</b><br>€%{x:,.0f}<extra></extra>"))
    layout_base(fig, "💳 Top 10 Categorías Gasto TC (histórico)")
    fig.update_layout(xaxis_title="EUR total", yaxis_title="", showlegend=False)
    return fig


@callback(Output("g-adv-ahorro","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_adv_ahorro(anio, trim, mes):
    dff_cc  = filtrar(df_cc_adv,     anio, trim, mes).sort_values("fecha")
    dff_tc  = filtrar(df_tc_mes_adv, anio, trim, mes).sort_values("fecha")
    dff_ing = filtrar(df_ing_adv,    anio, trim, mes).sort_values("fecha")
    if dff_ing.empty:
        return layout_base(go.Figure(), "💰 Tasa de Ahorro Real (CC + TC)")
    merged = dff_ing.merge(dff_cc[["fecha","gastos_cc"]], on="fecha", how="left"
        ).merge(dff_tc[["fecha","gastos_tc"]], on="fecha", how="left").fillna(0)
    merged["label"] = merged.apply(lambda r: lbl(r.anio, r.mes), axis=1)
    merged["total_gastos"] = merged["gastos_cc"] + merged["gastos_tc"]
    merged["ahorro"] = merged["ingresos"] - merged["total_gastos"]
    merged["tasa"] = (merged["ahorro"] / merged["ingresos"] * 100).round(1)
    colores = [VERDE if t > 0 else ROJO for t in merged["tasa"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=merged["label"], y=merged["tasa"], marker_color=colores,
        name="Tasa ahorro", hovertemplate="<b>%{x}</b><br>Tasa: %{y:.1f}%<extra></extra>"))
    fig.add_hline(y=0, line_color=TEXTO, line_width=1.5)
    fig.add_hline(y=20, line_dash="dash", line_color=VERDE, opacity=0.5,
                  annotation_text="Meta 20%", annotation_font_color=VERDE)
    if len(merged) > 0:
        prom = merged["tasa"].mean()
        fig.add_hline(y=prom, line_dash="dot", line_color=DORADO, opacity=0.7,
                      annotation_text=f"Prom. {prom:.1f}%", annotation_font_color=DORADO)
    layout_base(fig, "💰 Tasa de Ahorro Real Mensual (CC + TC)")
    fig.update_layout(yaxis_title="% de ahorro", xaxis_tickangle=45, showlegend=False)
    return fig


@callback(Output("g-adv-top10","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_adv_top10(anio, trim, mes):
    df = df_top10.copy().sort_values("total_eur")
    cat_colors = {"alimentacion":AZUL_C,"transporte":VERDE,"salud_deporte":NARANJA,
                  "servicios":DORADO,"alojamiento":GRIS,"comercio":PURPURA}
    colores = [cat_colors.get(c, ACENTO) for c in df["categoria_padre"]]
    fig = go.Figure(go.Bar(x=df["total_eur"], y=df["nombre"], orientation="h",
        marker_color=colores, customdata=df[["subcategoria","n"]].values,
        hovertemplate="<b>%{y}</b><br>€%{x:,.0f}<br>%{customdata[0]} · %{customdata[1]} transacciones<extra></extra>"))
    layout_base(fig, "🏆 Top 10 Comercios por Gasto Total")
    fig.update_layout(xaxis_title="EUR total", yaxis_title="", showlegend=False, height=380)
    return fig


@callback(Output("g-adv-proyeccion","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_adv_proyeccion(anio, trim, mes):
    from datetime import date as date_cls
    tc_actual    = 1070.0
    saldo_actual = SALDO_CLP / tc_actual
    cuota_eur_v  = CUOTA_CLP / tc_actual
    hoy          = date_cls.today()
    dff = filtrar(df_deuda, anio, trim, mes).sort_values("fecha")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dff["label"], y=dff["amort_deuda"],
        name="Amort. Deuda TC", marker_color=NARANJA, opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Amort.: €%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(x=dff["label"], y=dff["intereses"],
        name="Intereses", marker_color=DORADO, opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Intereses: €%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=dff["label"], y=dff["saldo_pendiente"],
        mode="lines+markers", name="Saldo pendiente",
        line=dict(color=ACENTO, width=2.5), yaxis="y2",
        hovertemplate="<b>%{x}</b><br>Saldo: €%{y:,.0f}<extra></extra>"))
    fechas_a, saldos_a = [], []
    saldo_tmp = saldo_actual
    for i in range(28):
        mes_p  = (hoy.month + i) % 12 + 1
        anio_p = hoy.year + (hoy.month + i) // 12
        fechas_a.append(lbl(anio_p, mes_p))
        saldos_a.append(max(0, saldo_tmp))
        int_mes   = saldo_tmp * TASA_MENSUAL
        amort_mes = cuota_eur_v - int_mes
        saldo_tmp -= amort_mes
    fig.add_trace(go.Scatter(x=fechas_a, y=saldos_a, mode="lines",
        name="Escenario A: seguir cuotas",
        line=dict(color=ROJO, width=2, dash="dash"), yaxis="y2",
        hovertemplate="<b>%{x}</b><br>Saldo proyectado: €%{y:,.0f}<extra></extra>"))
    fechas_b, saldos_b = [], []
    saldo_tmp2 = saldo_actual
    for i in range(7):
        mes_p  = (hoy.month + i) % 12 + 1
        anio_p = hoy.year + (hoy.month + i ) // 12
        fechas_b.append(lbl(anio_p, mes_p))
        saldos_b.append(max(0, saldo_tmp2))
        int_mes   = saldo_tmp2 * TASA_MENSUAL
        amort_mes = cuota_eur_v - int_mes
        saldo_tmp2 -= amort_mes
    fechas_b.append(f"Dic {LIQUIDACION_ANIO}")
    saldos_b.append(0)
    fig.add_trace(go.Scatter(x=fechas_b, y=saldos_b, mode="lines+markers",
        name="Escenario B: liquidar dic 2026",
        line=dict(color=VERDE, width=2.5, dash="dot"), yaxis="y2",
        hovertemplate="<b>%{x}</b><br>Saldo: €%{y:,.0f}<extra></extra>"))
    fig.add_annotation(x=f"Dic {LIQUIDACION_ANIO}", y=0,
        text=f"<b>Liquidación</b><br>Ahorro: €666",
        showarrow=True, arrowhead=2, arrowcolor=VERDE,
        font=dict(color=VERDE, size=10), bgcolor=FONDO2, bordercolor=VERDE, yref="y2")
    layout_base(fig, "💳 Proyección Liquidación Deuda TC — Escenario A vs B", height=400)
    fig.update_layout(
        barmode="stack", yaxis_title="EUR / mes",
        yaxis2=dict(title=dict(text="Saldo pendiente (EUR)", font=dict(color=ACENTO)),
                    overlaying="y", side="right", gridcolor="rgba(0,0,0,0)",
                    tickfont=dict(size=9, color=ACENTO)),
        xaxis_tickangle=45,
        legend=dict(orientation="h", yanchor="top", y=-0.25,
                    xanchor="center", x=0.5, font=dict(size=9, color=TEXTO)),
        margin=dict(t=45, b=100, l=55, r=60),
    )
    return fig


# ── Callbacks sección Madrid ───────────────────────────────────────────────────
@callback(Output("kpis-madrid","children"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_kpis_madrid(anio, trim, mes):
    if df_ing_mad.empty:
        return html.P("Sin datos de ingresos Madrid", style={"color":GRIS})

    row = df_ing_mad.iloc[0]
    neto_base    = row["neto_mensual_eur"]
    flex_comida  = row["flex_comida_eur"]
    flex_transp  = row["flex_transporte_eur"]
    beneficio_st = 28.35
    ingreso_total = neto_base + flex_comida + flex_transp + beneficio_st

    hoy = date.today()
    fin_prueba = date(2026, 11, 18)
    en_prueba = hoy < fin_prueba

    conn_k = get_conn()
    df_gm_local = pd.read_sql("SELECT * FROM gastos_fijos_madrid", conn_k)
    df_inv_local = pd.read_sql("SELECT * FROM inversiones", conn_k)
    conn_k.close()

    gastos_fijos = 0
    for _, g in df_gm_local.iterrows():
        fi_raw = g["fecha_inicio"]
        ff_raw = g["fecha_fin"]
        fi = pd.to_datetime(fi_raw).date() if fi_raw and str(fi_raw) != "None" else None
        ff = pd.to_datetime(ff_raw).date() if ff_raw and str(ff_raw) != "None" else None
        if fi and hoy >= fi:
            if ff is None or hoy < ff:
                gastos_fijos += g["importe_eur"]

    aportacion_inv = df_inv_local["aportacion_mensual_eur"].sum() if not df_inv_local.empty else 0
    capital_inv    = df_inv_local["capital_eur"].sum() if not df_inv_local.empty else 0
    ahorro = ingreso_total - gastos_fijos - aportacion_inv

    ratio_ahorro = ahorro / ingreso_total if ingreso_total > 0 else 0
    score = min(100, round(
        ratio_ahorro * 40 +
        (1 if ahorro > 0 else 0) * 20 +
        min(capital_inv / 10000, 1) * 20 +
        (1 if not en_prueba else 0.5) * 20
    , 0))
    score_color = VERDE if score >= 70 else NARANJA if score >= 40 else ROJO
    score_label = "Bueno" if score >= 70 else "Regular" if score >= 40 else "Bajo"

    return html.Div([
        kpi("Ingreso efectivo",     f"€{ingreso_total:,.0f}", "neto + flex + Santander", VERDE),
        kpi("Gastos fijos",         f"€{gastos_fijos:,.0f}",  "arriendo + servicios + ocio", ROJO),
        kpi("Aportación inversión", f"€{aportacion_inv:,.0f}","Mediolanum mensual", AZUL_C),
        kpi("Ahorro mensual",
            f"{'+'if ahorro>=0 else ''}€{ahorro:,.0f}",
            "después de gastos e inversión",
            VERDE if ahorro >= 0 else ROJO),
        kpi("Capital invertido",    f"€{capital_inv:,.0f}",   "Mediolanum total", DORADO),
        kpi(f"Score financiero",    f"{score}/100 — {score_label}",
            "Prueba" if en_prueba else "Post-prueba", score_color),
    ], style={"display":"flex","gap":"12px","flexWrap":"wrap"})


@callback(Output("g-mad-flujo","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_mad_flujo(anio, trim, mes):
    conn = get_conn()
    try:
        row = pd.read_sql("SELECT * FROM ingresos_madrid LIMIT 1", conn).iloc[0]
        df_inv_local = pd.read_sql("SELECT * FROM inversiones", conn)
    except:
        conn.close()
        return layout_base(go.Figure(), "💶 Flujo Mensual Madrid")
    conn.close()

    ingreso = row["neto_mensual_eur"] + row["flex_comida_eur"] + row["flex_transporte_eur"] + 28.35
    aportacion = df_inv_local["aportacion_mensual_eur"].sum()

    inicio = date(2026, 5, 1)
    meses_list = [inicio + relativedelta(months=i) for i in range(12)]
    labels = [f"{MESES_ES[m.month]} {m.year}" for m in meses_list]
    fin_prueba = date(2026, 11, 1)

    conceptos_vals = {
        "Arriendo":           [432 if m < fin_prueba else 865 for m in meses_list],
        "Internet + TV + 5G": [75]*12,
        "Agua + Luz + Gas":   [80]*12,
        "Gimnasio":           [67]*12,
        "Claude Pro":         [20]*12,
    }

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Ingreso neto total", x=labels, y=[ingreso]*12,
        marker_color=VERDE, opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Ingreso: €%{y:,.0f}<extra></extra>",
    ))
    colores_gastos = {
        "Arriendo": ROJO, "Internet + TV + 5G": AZUL,
        "Agua + Luz + Gas": AZUL_C, "Gimnasio": NARANJA, "Claude Pro": GRIS,
    }
    for concepto, valores in conceptos_vals.items():
        fig.add_trace(go.Bar(
            name=concepto, x=labels, y=valores,
            marker_color=colores_gastos.get(concepto, PURPURA), opacity=0.85,
            hovertemplate=f"<b>%{{x}}</b><br>{concepto}: €%{{y:,.0f}}<extra></extra>",
        ))
    ahorros = [ingreso - sum(v[i] for v in conceptos_vals.values()) - aportacion
               for i in range(12)]
    fig.add_trace(go.Scatter(
        x=labels, y=ahorros, mode="lines+markers", name="Ahorro mensual",
        line=dict(color=DORADO, width=2.5),
        hovertemplate="<b>%{x}</b><br>Ahorro: €%{y:,.0f}<extra></extra>",
    ))
    fig.add_annotation(x="Nov 2026", y=ingreso*0.9,
                      text="Fin período prueba", showarrow=True,
                      arrowhead=2, arrowcolor=NARANJA,
                      font=dict(color=NARANJA, size=10),
                      bgcolor=FONDO2, bordercolor=NARANJA)
    layout_base(fig, "💶 Flujo Mensual Madrid — Ingresos vs Gastos")
    fig.update_layout(
       barmode="group", yaxis_title="EUR / mes", xaxis_tickangle=45,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=FONDO2,
        legend=dict(orientation="h", yanchor="top", y=-0.25,
                    xanchor="center", x=0.5, font=dict(size=9, color=TEXTO)),
        margin=dict(t=45, b=100, l=55, r=20),
    )
    return fig


@callback(Output("g-mad-proyeccion","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_mad_proyeccion(anio, trim, mes):
    conn = get_conn()
    try:
        row = pd.read_sql("SELECT * FROM ingresos_madrid LIMIT 1", conn).iloc[0]
        df_inv_local = pd.read_sql("SELECT * FROM inversiones", conn)
    except Exception as e:
        conn.close()
        print(f"ERROR cb_mad_proyeccion: {e}")
        return layout_base(go.Figure(), "📈 Proyección Ahorro Acumulado")
    conn.close()

    ingreso = row["neto_mensual_eur"] + row["flex_comida_eur"] + row["flex_transporte_eur"] + 28.35
    aportacion = df_inv_local["aportacion_mensual_eur"].sum() if not df_inv_local.empty else 0

    inicio = date(2026, 5, 1)
    meses_list = [inicio + relativedelta(months=i) for i in range(24)]
    labels = [f"{MESES_ES[m.month]} {m.year}" for m in meses_list]
    fin_prueba = date(2026, 11, 1)

    acumulado = []
    total = 0
    for m in meses_list:
        arriendo = 432 if m < fin_prueba else 865
        otros = 75 + 80 + 67 + 20
        ahorro_mes = ingreso - arriendo - otros - aportacion
        total += ahorro_mes
        acumulado.append(round(total, 0))

    colores = [VERDE if v >= 0 else ROJO for v in acumulado]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=acumulado, marker_color=colores, opacity=0.75,
        name="Ahorro acumulado",
        hovertemplate="<b>%{x}</b><br>Acumulado: €%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=labels, y=acumulado, mode="lines",
        name="Tendencia", line=dict(color=DORADO, width=2),
        hovertemplate="<b>%{x}</b><br>€%{y:,.0f}<extra></extra>"))
    fig.add_hline(y=0, line_color=TEXTO, line_width=1.5)
    fig.add_annotation(x="Nov 2026", y=max(acumulado)*0.8,
                      text="Arriendo completo", showarrow=True,
                      arrowhead=2, arrowcolor=NARANJA,
                      font=dict(color=NARANJA, size=10),
                      bgcolor=FONDO2, bordercolor=NARANJA)
    fig = layout_base(fig, "📈 Proyección Ahorro Acumulado — 24 meses")
    fig.update_layout(yaxis_title="EUR acumulado", xaxis_tickangle=45,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=FONDO2)
    return fig


@callback(Output("g-mad-inversion","figure"),
          Input("f-anio","value"), Input("f-trim","value"), Input("f-mes","value"))
def cb_mad_inversion(anio, trim, mes):
    if df_inv.empty:
        return layout_base(go.Figure(), "💰 Proyección Inversión Mediolanum")

    tae_estimado = 0.025
    inicio = date(2026, 5, 1)
    meses_list = [inicio + relativedelta(months=i) for i in range(24)]
    labels = [f"{MESES_ES[m.month]} {m.year}" for m in meses_list]

    capital = 3000.0
    aportacion = 180.0
    tasa_mensual = tae_estimado / 12

    capitales, aportaciones_acum, rendimientos_acum = [], [], []
    aport_total = 0
    rend_total = 0
    for i in range(24):
        rendimiento = capital * tasa_mensual
        rend_total += rendimiento
        capital = capital + rendimiento + aportacion
        aport_total += aportacion
        capitales.append(round(capital, 0))
        aportaciones_acum.append(round(3000 + aport_total, 0))
        rendimientos_acum.append(round(rend_total, 0))

    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=aportaciones_acum, name="Capital + Aportaciones",
        marker_color=AZUL_C, opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Aportado: €%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(x=labels, y=rendimientos_acum, name="Rendimiento acumulado",
        marker_color=VERDE, opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Rendimiento: €%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=labels, y=capitales, mode="lines+markers",
        name="Capital total", line=dict(color=DORADO, width=2.5),
        hovertemplate="<b>%{x}</b><br>Capital: €%{y:,.0f}<extra></extra>"))
    fig.add_annotation(x=labels[-1], y=capitales[-1],
        text=f"<b>€{capitales[-1]:,.0f}</b>",
        showarrow=True, arrowhead=2, font=dict(color=DORADO, size=11),
        bgcolor=FONDO2, bordercolor=DORADO)

    layout_base(fig, f"💰 Proyección Inversión Mediolanum — TAE estimado {tae_estimado*100:.1f}%")
    fig.update_layout(
        barmode="stack", yaxis_title="EUR", xaxis_tickangle=45,
        legend=dict(orientation="h", yanchor="top", y=-0.2,
                    xanchor="center", x=0.5, font=dict(size=9, color=TEXTO)),
        margin=dict(t=45, b=80, l=55, r=20),
    )
    return fig


if __name__ == "__main__":
    print("="*55)
    print("  Dashboard Financiero — Claudio Socias Paradiz")
    print("="*55)
    print("  Abre en tu navegador: http://127.0.0.1:8050")
    print("  Detener: Ctrl+C")
    print("="*55)
    import os
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host="0.0.0.0", port=port)
