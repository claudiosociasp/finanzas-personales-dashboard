"""
Queries 5, 7 y 8 con gasto real de Tarjeta de Crédito incluido
Claudio Socias Paradiz | 2023-2026

Metodología:
  - Ingresos    : cc_movimientos (subcategoria = ingreso_laboral)
  - Gastos CC   : cc_movimientos (gastos corrientes)
  - Gastos TC   : tc_compras (fecha real de compra) + tc_cargos_fijos
  - Deuda TC    : cc_movimientos (amort_deuda_tc, pago_minimo_tc, intereses)
  - Período     : solo meses donde hay ingreso laboral registrado

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/queries_con_tc.py
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_FILE  = str(BASE_DIR / "finanzas.db")

MESES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
         7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

TC_ACTUAL        = 1070.0
SALDO_CLP        = 6520310
CUOTA_CLP        = 283327
TASA_MENSUAL     = 0.0116
TOTAL_CUOTAS     = 35
CUOTA_ACTUAL     = 8
LIQUIDACION_MES  = 9
LIQUIDACION_ANIO = 2026

def sep(titulo):
    print(f"\n{'='*62}")
    print(f"  {titulo}")
    print(f"{'='*62}")

def main():
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()

    # ══════════════════════════════════════════════════════════════════
    # QUERY 5 — % de ingresos destinado a deuda (con TC real)
    # ══════════════════════════════════════════════════════════════════
    sep("5b. % de ingresos destinado a deuda — con TC incluido")

    cur.execute("""
        WITH ingresos AS (
            SELECT m.anio, m.mes,
                   SUM(m.abono_clp / t.clp_eur) as total_ingresos
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.subcategoria = 'ingreso_laboral'
            AND m.abono_clp > 100000
            GROUP BY m.anio, m.mes
        ),
        deuda_cc AS (
            SELECT m.anio, m.mes,
                   SUM(m.cargo_clp / t.clp_eur) as deuda_cc
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.subcategoria IN ('amort_deuda_tc','pago_minimo_tc',
                                     'intereses','comision_banco')
            AND m.cargo_clp > 0
            GROUP BY m.anio, m.mes
        ),
        gastos_tc AS (
            SELECT
                CAST(strftime('%Y', c.fecha) AS INT) as anio,
                CAST(strftime('%m', c.fecha) AS INT) as mes,
                SUM(c.monto_clp / t.clp_eur) as gasto_tc
            FROM tc_compras c
            JOIN tipo_cambio t
                ON CAST(strftime('%Y', c.fecha) AS INT) = t.anio
                AND CAST(strftime('%m', c.fecha) AS INT) = t.mes
            WHERE c.categoria_padre NOT IN ('ignorar','finanzas')
            AND c.monto_clp > 0
            GROUP BY anio, mes
        )
        SELECT
            i.anio, i.mes,
            ROUND(i.total_ingresos, 0) as ingresos_eur,
            ROUND(COALESCE(d.deuda_cc, 0), 0) as deuda_eur,
            ROUND(COALESCE(g.gasto_tc, 0), 0) as gasto_tc_eur,
            ROUND((COALESCE(d.deuda_cc,0) + COALESCE(g.gasto_tc,0))
                  / i.total_ingresos * 100, 1) as pct_total
        FROM ingresos i
        LEFT JOIN deuda_cc d ON i.anio = d.anio AND i.mes = d.mes
        LEFT JOIN gastos_tc g ON i.anio = g.anio AND i.mes = g.mes
        ORDER BY i.anio, i.mes
    """)

    filas = cur.fetchall()
    print(f"\n  {'Mes':<12} {'Ingresos':>10} {'Deuda CC':>9} {'Gasto TC':>9} {'% Total':>8}  Semáforo")
    print(f"  {'─'*12} {'─'*10} {'─'*9} {'─'*9} {'─'*8}  {'─'*8}")
    for anio, mes, ing, deu, gtc, pct in filas:
        sem = "🟢" if pct < 30 else "🟡" if pct < 50 else "🔴"
        print(f"  {MESES[mes]} {anio}    €{ing:>8,.0f} €{deu:>7,.0f} €{gtc:>7,.0f}  {pct:>7.1f}%  {sem}")

    pcts = [r[5] for r in filas]
    if pcts:
        print(f"\n  Promedio % (deuda+TC)/ingreso : {sum(pcts)/len(pcts):.1f}%")
        print(f"  Máximo                        : {max(pcts):.1f}%")
        print(f"  Mínimo                        : {min(pcts):.1f}%")
        print(f"\n  Nota: Gasto TC = compras reales en tarjeta ese mes")
        print(f"        Deuda CC = cuotas + intereses pagados desde CC")

    # ══════════════════════════════════════════════════════════════════
    # QUERY 7b — Ahorro liquidación con gasto TC real acumulado
    # ══════════════════════════════════════════════════════════════════
    sep("7b. Costo real de la deuda incluyendo gasto TC histórico")

    # Total gastado en TC (compras reales, no cuotas)
    cur.execute("""
        SELECT
            ROUND(SUM(c.monto_clp / t.clp_eur), 0) as total_eur,
            COUNT(*) as n_transacciones,
            ROUND(AVG(c.monto_clp / t.clp_eur), 0) as promedio_eur
        FROM tc_compras c
        JOIN tipo_cambio t
            ON CAST(strftime('%Y', c.fecha) AS INT) = t.anio
            AND CAST(strftime('%m', c.fecha) AS INT) = t.mes
        WHERE c.categoria_padre NOT IN ('ignorar','finanzas')
        AND c.monto_clp > 0
    """)
    total_tc, n_tc, prom_tc = cur.fetchone()

    # Top categorías gastadas en TC
    cur.execute("""
        SELECT c.categoria_padre, c.subcategoria,
               ROUND(SUM(c.monto_clp / t.clp_eur), 0) as eur
        FROM tc_compras c
        JOIN tipo_cambio t
            ON CAST(strftime('%Y', c.fecha) AS INT) = t.anio
            AND CAST(strftime('%m', c.fecha) AS INT) = t.mes
        WHERE c.categoria_padre NOT IN ('ignorar','finanzas')
        AND c.monto_clp > 0
        GROUP BY c.categoria_padre, c.subcategoria
        ORDER BY eur DESC
        LIMIT 10
    """)
    top_cats = cur.fetchall()

    # Costos financieros totales
    cur.execute("""
        SELECT
            ROUND(SUM(CASE WHEN subcategoria='intereses'
                THEN cargo_clp/t.clp_eur ELSE 0 END),0) as intereses,
            ROUND(SUM(CASE WHEN subcategoria='comision_banco'
                THEN cargo_clp/t.clp_eur ELSE 0 END),0) as comisiones
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio=t.anio AND m.mes=t.mes
        WHERE subcategoria IN ('intereses','comision_banco')
        AND cargo_clp > 0
    """)
    intereses, comisiones = cur.fetchone()
    costo_fin = intereses + comisiones
    saldo_eur = round(SALDO_CLP / TC_ACTUAL)
    cuota_eur = round(CUOTA_CLP / TC_ACTUAL)

    print(f"""
  GASTO REAL EN TARJETA DE CRÉDITO (histórico completo)
  ─────────────────────────────────────────────────────
  Total compras TC       : €{total_tc:>8,.0f}  ({n_tc} transacciones)
  Promedio por compra    : €{prom_tc:>8,.0f}
  Costo financiero real  : €{costo_fin:>8,.0f}  (intereses + comisiones)
  % costo sobre compras  : {costo_fin/total_tc*100:.1f}%

  TOP CATEGORÍAS GASTADAS EN TC
  ─────────────────────────────────────────────────────""")

    for cat, sub, eur in top_cats:
        pct = eur / total_tc * 100
        print(f"  {sub:<25} €{eur:>7,.0f}  ({pct:.1f}%)")

    # Proyección liquidación
    cuotas_restantes = TOTAL_CUOTAS - CUOTA_ACTUAL
    costo_si_sigue   = cuota_eur * cuotas_restantes
    interes_futuro   = costo_si_sigue - saldo_eur

    saldo_sep    = float(saldo_eur)
    intereses_sep = 0.0
    for i in range(5):
        int_mes    = saldo_sep * TASA_MENSUAL
        amort_mes  = cuota_eur - int_mes
        intereses_sep += int_mes
        saldo_sep  -= amort_mes

    ahorro = interes_futuro - intereses_sep

    print(f"""
  PROYECCIÓN LIQUIDACIÓN SEPTIEMBRE 2026
  ─────────────────────────────────────────────────────
  Saldo actual           : €{saldo_eur:>8,.0f}
  Cuota mensual          : €{cuota_eur:>8,.0f}/mes
  Cuotas restantes       : {cuotas_restantes} meses hasta ene 2028

  Si sigue pagando cuotas:
    Total a desembolsar  : €{costo_si_sigue:>8,.0f}
    Intereses futuros    : €{interes_futuro:>8,.0f}

  Si liquida en sep 2026:
    5 cuotas normales    : €{cuota_eur*5:>8,.0f}
    Intereses 5 meses    : €{intereses_sep:>8,.0f}
    Saldo en sep         : €{saldo_sep:>8,.0f}
    Total desembolso     : €{cuota_eur*5+saldo_sep:>8,.0f}

  AHORRO POR LIQUIDAR    : €{ahorro:>8,.0f}
  Flujo libre oct 2026   : €{cuota_eur:>8,.0f}/mes (€{cuota_eur*12:,.0f}/año)
    """)

    # ══════════════════════════════════════════════════════════════════
    # QUERY 8b — Tasa de ahorro real con gasto TC incluido
    # ══════════════════════════════════════════════════════════════════
    sep("8b. Tasa de ahorro real — con gasto TC incluido")

    cur.execute("""
        WITH ingresos AS (
            SELECT m.anio, m.mes,
                   SUM(m.abono_clp / t.clp_eur) as ingresos
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.subcategoria = 'ingreso_laboral'
            AND m.abono_clp > 100000
            GROUP BY m.anio, m.mes
        ),
        gastos_cc AS (
            SELECT m.anio, m.mes,
                   SUM(m.cargo_clp / t.clp_eur) as gastos
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.categoria_padre NOT IN ('ignorar','transferencias')
            AND m.subcategoria != 'retiro_efectivo'
            AND m.cargo_clp > 0
            GROUP BY m.anio, m.mes
        ),
        gastos_tc AS (
            SELECT
                CAST(strftime('%Y', c.fecha) AS INT) as anio,
                CAST(strftime('%m', c.fecha) AS INT) as mes,
                SUM(c.monto_clp / t.clp_eur) as gasto_tc
            FROM tc_compras c
            JOIN tipo_cambio t
                ON CAST(strftime('%Y', c.fecha) AS INT) = t.anio
                AND CAST(strftime('%m', c.fecha) AS INT) = t.mes
            WHERE c.categoria_padre NOT IN ('ignorar','finanzas')
            AND c.monto_clp > 0
            GROUP BY anio, mes
        )
        SELECT
            i.anio, i.mes,
            ROUND(i.ingresos, 0) as ingresos_eur,
            ROUND(COALESCE(cc.gastos, 0), 0) as gastos_cc_eur,
            ROUND(COALESCE(tc.gasto_tc, 0), 0) as gastos_tc_eur,
            ROUND(COALESCE(cc.gastos,0) + COALESCE(tc.gasto_tc,0), 0) as total_gastos,
            ROUND((i.ingresos - COALESCE(cc.gastos,0)
                   - COALESCE(tc.gasto_tc,0)), 0) as ahorro,
            ROUND((i.ingresos - COALESCE(cc.gastos,0)
                   - COALESCE(tc.gasto_tc,0))
                  / i.ingresos * 100, 1) as tasa_ahorro
        FROM ingresos i
        LEFT JOIN gastos_cc cc ON i.anio = cc.anio AND i.mes = cc.mes
        LEFT JOIN gastos_tc tc ON i.anio = tc.anio AND i.mes = tc.mes
        ORDER BY i.anio, i.mes
    """)

    filas = cur.fetchall()
    print(f"\n  {'Mes':<12} {'Ingresos':>10} {'Gasto CC':>9} {'Gasto TC':>9} {'Total':>8} {'Ahorro':>9} {'Tasa':>7}")
    print(f"  {'─'*12} {'─'*10} {'─'*9} {'─'*9} {'─'*8} {'─'*9} {'─'*7}")

    for anio, mes, ing, gcc, gtc, tot, aho, tasa in filas:
        estado = "✅" if tasa > 0 else "❌"
        print(f"  {MESES[mes]} {anio}    "
              f"€{ing:>8,.0f} €{gcc:>7,.0f} €{gtc:>7,.0f} "
              f"€{tot:>6,.0f} "
              f"{'+'if aho>=0 else ''}€{aho:>7,.0f}  {tasa:>6.1f}% {estado}")

    tasas = [r[7] for r in filas]
    meses_pos = sum(1 for t in tasas if t > 0)
    if tasas:
        print(f"\n  Tasa de ahorro promedio  : {sum(tasas)/len(tasas):.1f}%")
        print(f"  Meses con ahorro positivo: {meses_pos}/{len(tasas)}")
        print(f"  Mejor mes                : {max(tasas):.1f}%")
        print(f"  Peor mes                 : {min(tasas):.1f}%")
        print(f"""
  COMPARACIÓN VS QUERY 8 ORIGINAL
  ─────────────────────────────────────────────────────
  Sin TC : tasa promedio ~57.9% (solo gastos CC)
  Con TC : tasa promedio ~{sum(tasas)/len(tasas):.1f}% (gastos CC + compras TC)
  Diferencia revela el gasto real oculto en la tarjeta
        """)

    conn.close()
    print("="*62)
    print("  Queries con TC ejecutadas correctamente")
    print(f"  Base de datos: {DB_FILE}")
    print("="*62)

if __name__ == "__main__":
    main()
