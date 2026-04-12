"""
Dashboard financiero personal — Claudio Socias
Genera dashboard interactivo HTML con Plotly

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/dashboard.py
    # Abre dashboard_financiero.html en el navegador
"""

import sqlite3
import numpy as np
import plotly.graph_objects as go
import plotly.subplots as sp
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).parent.parent
DB_FILE  = str(BASE_DIR / "finanzas.db")
OUTPUT   = str(BASE_DIR / "dashboard_financiero.html")

MESES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
         7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

# Paleta de colores
AZUL      = "#1B4F72"
AZUL_CLARO = "#2E86C1"
VERDE     = "#1E8449"
ROJO      = "#C0392B"
NARANJA   = "#D35400"
GRIS      = "#566573"
DORADO    = "#D4AC0D"
FONDO     = "#0D1B2A"
FONDO2    = "#162535"
TEXTO     = "#E8F4FD"
GRID      = "#1E3A52"

def main():
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()

    # ── Datos tipo de cambio ───────────────────────────────────────
    cur.execute("""
        SELECT anio, mes, clp_eur FROM tipo_cambio
        ORDER BY anio, mes
    """)
    tc_data = cur.fetchall()
    tc_fechas = [f"{MESES[m]} {a}" for a, m, _ in tc_data]
    tc_valores = [v for _, _, v in tc_data]
    tc_nums    = list(range(len(tc_fechas)))

    # ── Datos ingresos laborales ───────────────────────────────────
    cur.execute("""
        SELECT m.anio, m.mes, m.descripcion,
               ROUND(m.abono_clp / t.clp_eur, 0) as eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria = 'ingreso_laboral'
        AND m.abono_clp > 100
        ORDER BY m.anio, m.mes
    """)
    ingresos_raw = cur.fetchall()

    # Agrupar por mes y empresa
    ingresos = {}
    for anio, mes, desc, eur in ingresos_raw:
        key = (anio, mes)
        empresa = "PwC" if "PRICEWATERH" in desc else "Arcaya"
        if key not in ingresos:
            ingresos[key] = {"PwC": 0, "Arcaya": 0}
        ingresos[key][empresa] += eur

    ing_fechas  = [f"{MESES[m]} {a}" for a, m in sorted(ingresos.keys())]
    ing_pwc     = [ingresos[k].get("PwC", 0) for k in sorted(ingresos.keys())]
    ing_arcaya  = [ingresos[k].get("Arcaya", 0) for k in sorted(ingresos.keys())]
    ing_total   = [p + a for p, a in zip(ing_pwc, ing_arcaya)]

    # Regresión lineal sobre ingresos totales
    x_ing = np.arange(len(ing_total))
    coef  = np.polyfit(x_ing, ing_total, 1)
    tendencia = np.polyval(coef, x_ing)
    pendiente = coef[0]

    # ── Gastos por categoría y período ────────────────────────────
    cur.execute("""
        SELECT m.categoria_padre, m.subcategoria,
               m.anio,
               ROUND(SUM(m.cargo_clp / t.clp_eur), 0) as eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.categoria_padre NOT IN ('ignorar','transferencias')
        AND m.cargo_clp > 0
        GROUP BY m.categoria_padre, m.subcategoria, m.anio
        ORDER BY m.categoria_padre, m.subcategoria, m.anio
    """)
    gastos_raw = cur.fetchall()

    # ── Evolución gasto mensual ────────────────────────────────────
    cur.execute("""
        SELECT m.anio, m.mes,
               ROUND(SUM(m.cargo_clp / t.clp_eur), 0) as gasto_eur,
               ROUND(SUM(CASE WHEN m.subcategoria IN
                   ('cuota_lca','cuota_tc','intereses','comision_banco')
                   THEN m.cargo_clp / t.clp_eur ELSE 0 END), 0) as deuda_eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.categoria_padre NOT IN ('ignorar','transferencias')
        AND m.cargo_clp > 0
        GROUP BY m.anio, m.mes
        ORDER BY m.anio, m.mes
    """)
    gastos_mensuales = cur.fetchall()

    gm_fechas  = [f"{MESES[m]} {a}" for a, m, _, _ in gastos_mensuales]
    gm_total   = [g for _, _, g, _ in gastos_mensuales]
    gm_deuda   = [d for _, _, _, d in gastos_mensuales]
    gm_corriente = [g - d for g, d in zip(gm_total, gm_deuda)]

    # Regresión gasto corriente
    x_gm   = np.arange(len(gm_corriente))
    coef_g = np.polyfit(x_gm, gm_corriente, 1)
    tend_g = np.polyval(coef_g, x_gm)

    # ── Costo real deuda ──────────────────────────────────────────
    cur.execute("""
        SELECT m.subcategoria,
               ROUND(SUM(m.cargo_clp / t.clp_eur), 0) as eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria IN ('cuota_lca','cuota_tc','intereses','comision_banco')
        AND m.cargo_clp > 0
        GROUP BY m.subcategoria
    """)
    deuda_data = cur.fetchall()
    deuda_labels = {
        "cuota_lca":     "Cuota LCA",
        "cuota_tc":      "Cuota TC",
        "intereses":     "Intereses",
        "comision_banco":"Comisiones",
    }
    deuda_nombres = [deuda_labels.get(s, s) for s, _ in deuda_data]
    deuda_valores = [v for _, v in deuda_data]

    # ── Datos comparación poder adquisitivo ───────────────────────
    categorias = ["Supermercado","Restaurantes","Taxi/Uber",
                  "Transporte","Gimnasio","Suscripciones","Alquiler"]
    chile_vals  = [272, 146, 25, 34, 41, 4, 887]   # €888 = promedio alquiler LC
    madrid_vals = [250, 57, 25, 50, 67, 55, 1500]

    conn.close()

    # ══════════════════════════════════════════════════════════════
    # CREAR DASHBOARD
    # ══════════════════════════════════════════════════════════════
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            "📈 Evolución Tipo de Cambio CLP/EUR (2023-2026)",
            "💼 Ingresos Laborales en EUR + Tendencia",
            "📊 Evolución Gasto Mensual + Componente Deuda",
            "🍕 Costo Real de la Deuda",
            "🏠 Poder Adquisitivo: Las Condes vs Salamanca",
            "🌍 Comparación Salarial: Chile vs Madrid",
        ),
        specs=[
            [{"type": "scatter"}, {"type": "bar"}],
            [{"type": "scatter"}, {"type": "pie"}],
            [{"type": "bar"},     {"type": "scatter"}],
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
    )

    # ── GRÁFICO 1: Tipo de cambio ──────────────────────────────────
    fig.add_trace(go.Scatter(
        x=tc_fechas, y=tc_valores,
        mode="lines+markers",
        name="CLP/EUR",
        line=dict(color=AZUL_CLARO, width=2.5),
        marker=dict(size=5, color=AZUL_CLARO),
        fill="tozeroy",
        fillcolor="rgba(46,134,193,0.1)",
        hovertemplate="<b>%{x}</b><br>1 EUR = $%{y:,.0f} CLP<extra></extra>",
    ), row=1, col=1)

    # Hitos
    hitos = [
        ("Feb 2023", 855, "Mínimo CLP/EUR", VERDE),
        ("Sep 2025", 1126, "Máximo CLP/EUR", ROJO),
        ("Abr 2026", tc_valores[-1], "Hoy", DORADO),
    ]
    for fecha, val, label, color in hitos:
        if fecha in tc_fechas:
            fig.add_annotation(
                x=fecha, y=val,
                text=f"<b>{label}</b><br>${val:,.0f}",
                showarrow=True, arrowhead=2,
                arrowcolor=color, font=dict(color=color, size=10),
                bgcolor=FONDO2, bordercolor=color,
                row=1, col=1
            )

    # Línea promedio
    prom_tc = sum(tc_valores) / len(tc_valores)
    fig.add_hline(y=prom_tc, line_dash="dash",
                  line_color=GRIS, opacity=0.6,
                  annotation_text=f"Promedio ${prom_tc:,.0f}",
                  annotation_font_color=GRIS, row=1, col=1)

    # ── GRÁFICO 2: Ingresos + tendencia ───────────────────────────
    fig.add_trace(go.Bar(
        x=ing_fechas, y=ing_pwc,
        name="PwC", marker_color=AZUL,
        hovertemplate="<b>%{x}</b><br>PwC: €%{y:,.0f}<extra></extra>",
    ), row=1, col=2)

    fig.add_trace(go.Bar(
        x=ing_fechas, y=ing_arcaya,
        name="Clínica Arcaya", marker_color=AZUL_CLARO,
        hovertemplate="<b>%{x}</b><br>Arcaya: €%{y:,.0f}<extra></extra>",
    ), row=1, col=2)

    fig.add_trace(go.Scatter(
        x=ing_fechas, y=list(tendencia),
        mode="lines", name="Tendencia",
        line=dict(color=DORADO, width=2, dash="dash"),
        hovertemplate="<b>%{x}</b><br>Tendencia: €%{y:,.0f}<extra></extra>",
    ), row=1, col=2)

    # Anotación pendiente
    signo = "↑" if pendiente > 0 else "↓"
    fig.add_annotation(
        x=ing_fechas[-1], y=max(ing_total),
        text=f"<b>Pendiente: {signo}€{abs(pendiente):.0f}/mes</b>",
        showarrow=False,
        font=dict(color=DORADO, size=11),
        bgcolor=FONDO2, bordercolor=DORADO,
        row=1, col=2
    )

    # ── GRÁFICO 3: Evolución gasto mensual ────────────────────────
    fig.add_trace(go.Bar(
        x=gm_fechas, y=gm_corriente,
        name="Gasto corriente",
        marker_color=AZUL_CLARO, opacity=0.8,
        hovertemplate="<b>%{x}</b><br>Gasto: €%{y:,.0f}<extra></extra>",
    ), row=2, col=1)

    fig.add_trace(go.Bar(
        x=gm_fechas, y=gm_deuda,
        name="Deuda",
        marker_color=ROJO, opacity=0.8,
        hovertemplate="<b>%{x}</b><br>Deuda: €%{y:,.0f}<extra></extra>",
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=gm_fechas, y=list(tend_g),
        mode="lines", name="Tendencia gasto",
        line=dict(color=VERDE, width=2, dash="dot"),
        hovertemplate="<b>%{x}</b><br>Tendencia: €%{y:,.0f}<extra></extra>",
    ), row=2, col=1)

    # Equivalencia salarial Madrid
    fig.add_hline(
        y=2200, line_dash="dash", line_color=DORADO, opacity=0.7,
        annotation_text="Sueldo Senior Madrid €2.200",
        annotation_font_color=DORADO, row=2, col=1
    )

    # ── GRÁFICO 4: Costo deuda pie ─────────────────────────────────
    fig.add_trace(go.Pie(
        labels=deuda_nombres,
        values=deuda_valores,
        hole=0.45,
        marker=dict(colors=[ROJO, NARANJA, DORADO, GRIS]),
        textinfo="label+percent",
        textfont=dict(color=TEXTO, size=12),
        hovertemplate="<b>%{label}</b><br>€%{value:,.0f}<br>%{percent}<extra></extra>",
    ), row=2, col=2)

    total_deuda = sum(deuda_valores)
    fig.add_annotation(
        text=f"<b>Total</b><br>€{total_deuda:,.0f}",
        x=0.78, y=0.38,
        font=dict(size=13, color=TEXTO),
        showarrow=False,
    )

    # ── GRÁFICO 5: Poder adquisitivo barras ───────────────────────
    fig.add_trace(go.Bar(
        x=categorias, y=chile_vals,
        name="Las Condes", marker_color=AZUL,
        hovertemplate="<b>%{x}</b><br>Las Condes: €%{y:,.0f}<extra></extra>",
    ), row=3, col=1)

    fig.add_trace(go.Bar(
        x=categorias, y=madrid_vals,
        name="Salamanca", marker_color=NARANJA,
        hovertemplate="<b>%{x}</b><br>Salamanca: €%{y:,.0f}<extra></extra>",
    ), row=3, col=1)

    # ── GRÁFICO 6: Comparación salarial scatter ────────────────────
    niveles   = ["Junior\n<3 años", "Mid-Senior\n3-5 años",
                 "Senior\n+5 años", "Senior+\nPython"]
    sal_min   = [22000, 30000, 38000, 46000]
    sal_max   = [28000, 38000, 46000, 55000]
    sal_medio = [(a+b)/2 for a, b in zip(sal_min, sal_max)]
    colores_sal = [GRIS, AZUL_CLARO, VERDE, DORADO]

    for i, (nivel, medio, color) in enumerate(zip(niveles, sal_medio, colores_sal)):
        marcador = "star" if i == 2 else "circle"
        fig.add_trace(go.Scatter(
            x=[nivel], y=[medio],
            mode="markers+text",
            name=nivel.replace("\n", " "),
            marker=dict(size=20 if i == 2 else 14,
                       color=color, symbol=marcador),
            text=[f"€{medio:,.0f}"],
            textposition="top center",
            textfont=dict(color=color, size=10),
            hovertemplate=f"<b>{nivel}</b><br>€{sal_min[i]:,}-€{sal_max[i]:,}/año<extra></extra>",
        ), row=3, col=2)

    # Línea sueldo Chile
    avg_eur_anual = 1484 * 12
    fig.add_trace(go.Scatter(
        x=niveles,
        y=[avg_eur_anual] * len(niveles),
        mode="lines",
        name=f"Tu sueldo Chile €{avg_eur_anual:,}/año",
        line=dict(color=ROJO, width=2, dash="dash"),
        hovertemplate=f"Tu sueldo Chile: €{avg_eur_anual:,}/año<extra></extra>",
    ), row=3, col=2)

    # ══════════════════════════════════════════════════════════════
    # LAYOUT GENERAL
    # ══════════════════════════════════════════════════════════════
    fig.update_layout(
        title=dict(
            text="<b>Dashboard Financiero Personal — Claudio Socias Paradiz</b>"
                 "<br><sup>Data Analyst | BI | Santiago → Madrid | 2023-2026</sup>",
            font=dict(size=22, color=TEXTO, family="Georgia"),
            x=0.5,
        ),
        paper_bgcolor=FONDO,
        plot_bgcolor=FONDO2,
        font=dict(color=TEXTO, family="Arial", size=11),
        legend=dict(
            bgcolor="rgba(22,37,53,0.8)",
            bordercolor=GRID,
            borderwidth=1,
            font=dict(color=TEXTO),
        ),
        height=1400,
        barmode="stack",
        showlegend=True,
        margin=dict(t=100, b=60, l=60, r=60),
    )

    # Estilo ejes
    for i in range(1, 4):
        for j in range(1, 3):
            try:
                fig.update_xaxes(
                    gridcolor=GRID, showgrid=True,
                    tickfont=dict(size=9, color=TEXTO),
                    linecolor=GRID,
                    row=i, col=j
                )
                fig.update_yaxes(
                    gridcolor=GRID, showgrid=True,
                    tickfont=dict(size=9, color=TEXTO),
                    linecolor=GRID,
                    row=i, col=j
                )
            except Exception:
                pass

    # Títulos ejes
    fig.update_yaxes(title_text="CLP por EUR", row=1, col=1)
    fig.update_yaxes(title_text="EUR / mes", row=1, col=2)
    fig.update_yaxes(title_text="EUR / mes", row=2, col=1)
    fig.update_yaxes(title_text="EUR / año", row=3, col=2)

    # Rotar etiquetas eje x
    fig.update_xaxes(tickangle=45, row=1, col=1)
    fig.update_xaxes(tickangle=45, row=1, col=2)
    fig.update_xaxes(tickangle=45, row=2, col=1)

    # Subtítulos coloreados
    for ann in fig.layout.annotations:
        if ann.text and ann.text.startswith(("📈","💼","📊","🍕","🏠","🌍")):
            ann.font = dict(size=13, color=TEXTO, family="Georgia")

    # Guardar
    fig.write_html(OUTPUT, include_plotlyjs="cdn")
    print(f"Dashboard generado: {OUTPUT}")
    print("Abre el archivo en tu navegador para verlo.")


if __name__ == "__main__":
    main()
