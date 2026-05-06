"""
Queries SQL avanzadas — Análisis financiero personal
Claudio Socias Paradiz | 2023-2026

Queries:
  1.  Ingreso real neto mensual promedio por empresa
  3.  Top 10 comercios por gasto total
  5.  % de ingresos destinado a deuda (solo CC)
  5b. % de ingresos destinado a deuda (CC + TC)
  6.  Intereses reales vs capital amortizado
  7.  Ahorro por liquidar en septiembre 2026
  8.  Tasa de ahorro real (solo CC)
  8b. Tasa de ahorro real (CC + TC)
  9.  Gasto corriente Madrid vs Las Condes

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/queries_avanzadas.py
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_FILE  = str(BASE_DIR / "finanzas.db")

MESES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
         7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

TC_ACTUAL        = 1070.0
SALDO_CLP        = 6312618
CUOTA_CLP        = 283327
TASA_MENSUAL     = 0.0116
TOTAL_CUOTAS     = 35
CUOTA_ACTUAL     = 9
LIQUIDACION_MES  = 9
LIQUIDACION_ANIO = 2026

# Ajustes manuales Chile (DB subestima por pagos con TC)
CHILE_AJUSTADO = {
    "supermercado":        272,
    "restaurante":         146,
    "transporte_publico":   34,
}

# Madrid ajustado (datos reales + INE 2024)
MADRID_AJUSTADO = {
    "supermercado":       250,
    "restaurante":         57,
    "transporte_publico":  50,
    "uber_taxi":           25,
    "bencina":              0,
    "gimnasio":            67,
    "suscripcion":         55,
}

def sep(titulo):
    print(f"\n{'='*62}")
    print(f"  {titulo}")
    print(f"{'='*62}")

def main():
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()

    # ══════════════════════════════════════════════════════════════
    # QUERY 1 — Ingreso real neto mensual promedio por empresa
    # ══════════════════════════════════════════════════════════════
    sep("1. Ingreso real neto mensual promedio por empresa")

    cur.execute("""
        SELECT
            CASE WHEN m.descripcion LIKE '%PRICEWATERH%'
                 THEN 'PricewaterhouseCoopers'
                 ELSE 'Clínica Lo Arcaya' END as empresa,
            COUNT(DISTINCT m.anio || '-' || m.mes) as meses_activos,
            ROUND(SUM(m.abono_clp), 0) as total_clp,
            ROUND(AVG(m.abono_clp), 0) as promedio_clp,
            ROUND(SUM(m.abono_clp / t.clp_eur), 0) as total_eur,
            ROUND(AVG(m.abono_clp / t.clp_eur), 0) as promedio_eur,
            ROUND(MIN(m.abono_clp / t.clp_eur), 0) as min_eur,
            ROUND(MAX(m.abono_clp / t.clp_eur), 0) as max_eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria = 'ingreso_laboral'
        AND m.abono_clp > 500000
        GROUP BY empresa
        ORDER BY promedio_eur DESC
    """)

    for emp, meses, tot_clp, prom_clp, tot_eur, prom_eur, min_eur, max_eur in cur.fetchall():
        print(f"\n  {emp}")
        print(f"    Meses activos    : {meses}")
        print(f"    Total recibido   : ${tot_clp:>12,.0f} CLP  ≈  €{tot_eur:>7,.0f}")
        print(f"    Promedio mensual : ${prom_clp:>12,.0f} CLP  ≈  €{prom_eur:>7,.0f}/mes")
        print(f"    Rango EUR        : €{min_eur:,.0f} — €{max_eur:,.0f}/mes")
        print(f"    Anualizado equiv : ≈ €{prom_eur*12:,.0f}/año bruto")

    cur.execute("""
        SELECT
            ROUND(AVG(CASE WHEN m.descripcion LIKE '%PRICEWATERH%'
                THEN m.abono_clp / t.clp_eur END), 0) as pwc_eur,
            ROUND(AVG(CASE WHEN m.descripcion LIKE '%762091712%'
                AND m.abono_clp BETWEEN 1400000 AND 1600000
                THEN m.abono_clp / t.clp_eur END), 0) as arcaya_base_eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria = 'ingreso_laboral'
        AND m.abono_clp > 500000
    """)
    pwc, arcaya = cur.fetchone()
    if pwc and arcaya:
        diff = arcaya - pwc
        pct  = (diff / pwc) * 100
        print(f"\n  Variación PwC → Arcaya base:")
        print(f"    PwC          : €{pwc:,.0f}/mes")
        print(f"    Arcaya base  : €{arcaya:,.0f}/mes")
        print(f"    Diferencia   : {'+'if diff>=0 else ''}€{diff:,.0f}/mes ({pct:+.1f}%)")

    # ══════════════════════════════════════════════════════════════
    # QUERY 3 — Top 10 comercios por gasto total
    # ══════════════════════════════════════════════════════════════
    sep("3. Top 10 comercios por gasto total")

    cur.execute("""
        SELECT
            m.descripcion,
            m.subcategoria,
            COUNT(*) as n,
            ROUND(SUM(m.cargo_clp / t.clp_eur), 0) as total_eur,
            ROUND(AVG(m.cargo_clp / t.clp_eur), 0) as promedio_eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.categoria_padre NOT IN ('ignorar','transferencias','finanzas')
        AND m.subcategoria != 'retiro_efectivo'
        AND m.cargo_clp > 0
        GROUP BY m.descripcion
        ORDER BY total_eur DESC
        LIMIT 10
    """)

    print(f"\n  {'#':<3} {'Comercio':<35} {'Cat':<15} {'N':>4} {'Total EUR':>10} {'Prom EUR':>9}")
    print(f"  {'─'*3} {'─'*35} {'─'*15} {'─'*4} {'─'*10} {'─'*9}")
    for i, (desc, sub, n, eur, prom) in enumerate(cur.fetchall(), 1):
        nombre = desc[:34] if len(desc) > 34 else desc
        print(f"  {i:<3} {nombre:<35} {sub:<15} {n:>4} €{eur:>9,.0f} €{prom:>8,.0f}")

    # ══════════════════════════════════════════════════════════════
    # QUERY 5 — % de ingresos destinado a deuda (solo CC)
    # ══════════════════════════════════════════════════════════════
    sep("5. % de ingresos destinado a deuda (solo CC)")

    cur.execute("""
        SELECT
            ing.anio, ing.mes,
            ROUND(ing.total_ingresos, 0) as ingresos_eur,
            ROUND(deu.total_deuda, 0) as deuda_eur,
            ROUND(deu.total_deuda / ing.total_ingresos * 100, 1) as pct_deuda
        FROM (
            SELECT m.anio, m.mes,
                   SUM(m.abono_clp / t.clp_eur) as total_ingresos
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.subcategoria = 'ingreso_laboral'
            AND m.abono_clp > 100000
            GROUP BY m.anio, m.mes
        ) ing
        JOIN (
            SELECT m.anio, m.mes,
                   SUM(m.cargo_clp / t.clp_eur) as total_deuda
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.subcategoria IN ('amort_deuda_tc','pago_minimo_tc',
                                     'intereses','comision_banco')
            AND m.cargo_clp > 0
            GROUP BY m.anio, m.mes
        ) deu ON ing.anio = deu.anio AND ing.mes = deu.mes
        ORDER BY ing.anio, ing.mes
    """)

    filas = cur.fetchall()
    print(f"\n  {'Mes':<12} {'Ingresos':>10} {'Deuda':>8} {'% Deuda':>8}  Semáforo")
    print(f"  {'─'*12} {'─'*10} {'─'*8} {'─'*8}  {'─'*8}")
    for anio, mes, ing, deu, pct in filas:
        sem = "🟢" if pct < 20 else "🟡" if pct < 35 else "🔴"
        print(f"  {MESES[mes]} {anio}    €{ing:>8,.0f} €{deu:>6,.0f}  {pct:>7.1f}%  {sem}")

    pcts = [r[4] for r in filas]
    if pcts:
        print(f"\n  Promedio % deuda/ingreso : {sum(pcts)/len(pcts):.1f}%")
        print(f"  Máximo                   : {max(pcts):.1f}%")
        print(f"  Mínimo                   : {min(pcts):.1f}%")

    # ══════════════════════════════════════════════════════════════
    # QUERY 5b — % de ingresos destinado a deuda (CC + TC)
    # ══════════════════════════════════════════════════════════════
    sep("5b. % de ingresos destinado a deuda — con TC incluido")

    cur.execute("""
        SELECT
            ing.anio, ing.mes,
            ROUND(ing.total_ingresos, 0) as ingresos_eur,
            ROUND(COALESCE(deu.deuda_cc, 0), 0) as deuda_eur,
            ROUND(COALESCE(gtc.gasto_tc, 0), 0) as gasto_tc_eur,
            ROUND((COALESCE(deu.deuda_cc,0) + COALESCE(gtc.gasto_tc,0))
                  / ing.total_ingresos * 100, 1) as pct_total
        FROM (
            SELECT m.anio, m.mes,
                   SUM(m.abono_clp / t.clp_eur) as total_ingresos
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.subcategoria = 'ingreso_laboral'
            AND m.abono_clp > 100000
            GROUP BY m.anio, m.mes
        ) ing
        LEFT JOIN (
            SELECT m.anio, m.mes,
                   SUM(m.cargo_clp / t.clp_eur) as deuda_cc
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.subcategoria IN ('amort_deuda_tc','pago_minimo_tc',
                                     'intereses','comision_banco')
            AND m.cargo_clp > 0
            GROUP BY m.anio, m.mes
        ) deu ON ing.anio = deu.anio AND ing.mes = deu.mes
        LEFT JOIN (
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
            GROUP BY CAST(strftime('%Y', c.fecha) AS INT),
                     CAST(strftime('%m', c.fecha) AS INT)
        ) gtc ON ing.anio = gtc.anio AND ing.mes = gtc.mes
        ORDER BY ing.anio, ing.mes
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

    # ══════════════════════════════════════════════════════════════
    # QUERY 6 — Intereses reales vs capital amortizado
    # ══════════════════════════════════════════════════════════════
    sep("6. Intereses reales vs capital amortizado")

    cur.execute("""
        SELECT
            ROUND(SUM(CASE WHEN m.subcategoria = 'amort_deuda_tc'
                THEN m.cargo_clp / t.clp_eur ELSE 0 END), 0) as capital_eur,
            ROUND(SUM(CASE WHEN m.subcategoria = 'pago_minimo_tc'
                THEN m.cargo_clp / t.clp_eur ELSE 0 END), 0) as pago_min_eur,
            ROUND(SUM(CASE WHEN m.subcategoria = 'intereses'
                THEN m.cargo_clp / t.clp_eur ELSE 0 END), 0) as intereses_eur,
            ROUND(SUM(CASE WHEN m.subcategoria = 'comision_banco'
                THEN m.cargo_clp / t.clp_eur ELSE 0 END), 0) as comisiones_eur,
            ROUND(SUM(m.cargo_clp / t.clp_eur), 0) as total_eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria IN ('amort_deuda_tc','pago_minimo_tc',
                                  'intereses','comision_banco')
        AND m.cargo_clp > 0
    """)

    cap, pago_min, inter, comis, total = cur.fetchone()
    costo_fin = inter + comis
    saldo_eur = round(SALDO_CLP / TC_ACTUAL)

    print(f"""
  DESGLOSE TOTAL PAGADO
  ─────────────────────────────────────────────────
  Amortización deuda TC  : €{cap:>8,.0f}  ({cap/total*100:.1f}%)
  Pagos mínimos TC       : €{pago_min:>8,.0f}  ({pago_min/total*100:.1f}%)
  Intereses              : €{inter:>8,.0f}  ({inter/total*100:.1f}%)
  Comisiones banco       : €{comis:>8,.0f}  ({comis/total*100:.1f}%)
  ─────────────────────────────────────────────────
  TOTAL PAGADO           : €{total:>8,.0f}

  ANÁLISIS COSTO FINANCIERO
  ─────────────────────────────────────────────────
  Capital pagado         : €{cap+pago_min:>8,.0f}
  Costo financiero real  : €{costo_fin:>8,.0f}  (intereses + comisiones)
  % costo sobre pagado   : {costo_fin/total*100:.1f}%
  Saldo pendiente actual : €{saldo_eur:>8,.0f}
  Deuda original estimada: €{cap+pago_min+saldo_eur:>8,.0f}
    """)

    # ══════════════════════════════════════════════════════════════
    # QUERY 7 — Ahorro por liquidar en septiembre 2026
    # ══════════════════════════════════════════════════════════════
    sep("7. Ahorro por liquidar en septiembre 2026 vs seguir en cuotas")

    saldo_eur_actual  = SALDO_CLP / TC_ACTUAL
    cuota_eur_actual  = CUOTA_CLP / TC_ACTUAL
    cuotas_restantes  = TOTAL_CUOTAS - CUOTA_ACTUAL

    costo_cuotas   = cuota_eur_actual * cuotas_restantes
    interes_futuro = costo_cuotas - saldo_eur_actual

    meses_hasta_sep = 5
    saldo_sep = saldo_eur_actual
    intereses_sep = 0.0
    for i in range(meses_hasta_sep):
        int_mes   = saldo_sep * TASA_MENSUAL
        amort_mes = cuota_eur_actual - int_mes
        intereses_sep += int_mes
        saldo_sep -= amort_mes

    ahorro = interes_futuro - intereses_sep

    print(f"""
  ESCENARIO A — Seguir pagando cuotas hasta el final
  ─────────────────────────────────────────────────
  Cuotas restantes      : {cuotas_restantes} cuotas (hasta {TOTAL_CUOTAS}/{TOTAL_CUOTAS})
  Cuota mensual         : €{cuota_eur_actual:,.0f}/mes
  Total a pagar         : €{costo_cuotas:,.0f}
  Capital pendiente     : €{saldo_eur_actual:,.0f}
  Intereses futuros     : €{interes_futuro:,.0f}
  Término estimado      : Enero 2028 aprox.

  ESCENARIO B — Liquidar en septiembre 2026
  ─────────────────────────────────────────────────
  Meses hasta sep 2026  : {meses_hasta_sep} cuotas normales
  Cuotas normales       : €{cuota_eur_actual*meses_hasta_sep:,.0f}
  Intereses en esos {meses_hasta_sep}m  : €{intereses_sep:,.0f}
  Saldo a pagar en sep  : €{saldo_sep:,.0f}
  Total desembolso      : €{cuota_eur_actual*meses_hasta_sep+saldo_sep:,.0f}

  COMPARACIÓN
  ─────────────────────────────────────────────────
  Ahorro en intereses   : €{ahorro:,.0f}
  Liberación flujo caja : €{cuota_eur_actual:,.0f}/mes desde oct {LIQUIDACION_ANIO}
  Valor anual flujo     : €{cuota_eur_actual*12:,.0f}/año liberados
    """)

    # ══════════════════════════════════════════════════════════════
    # QUERY 8 — Tasa de ahorro real (solo CC)
    # ══════════════════════════════════════════════════════════════
    sep("8. Tasa de ahorro real mes a mes (solo CC)")

    cur.execute("""
        SELECT
            ing.anio, ing.mes,
            ROUND(ing.ingresos, 0) as ingresos_eur,
            ROUND(gas.gastos, 0) as gastos_eur,
            ROUND(ing.ingresos - gas.gastos, 0) as ahorro_eur,
            ROUND((ing.ingresos - gas.gastos) / ing.ingresos * 100, 1) as tasa_ahorro
        FROM (
            SELECT m.anio, m.mes,
                   SUM(m.abono_clp / t.clp_eur) as ingresos
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.subcategoria = 'ingreso_laboral'
            AND m.abono_clp > 100000
            GROUP BY m.anio, m.mes
        ) ing
        JOIN (
            SELECT m.anio, m.mes,
                   SUM(m.cargo_clp / t.clp_eur) as gastos
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.categoria_padre NOT IN ('ignorar','transferencias')
            AND m.subcategoria != 'retiro_efectivo'
            AND m.cargo_clp > 0
            GROUP BY m.anio, m.mes
        ) gas ON ing.anio = gas.anio AND ing.mes = gas.mes
        ORDER BY ing.anio, ing.mes
    """)

    filas = cur.fetchall()
    print(f"\n  {'Mes':<12} {'Ingresos':>10} {'Gastos':>9} {'Ahorro':>9} {'Tasa':>7}  Estado")
    print(f"  {'─'*12} {'─'*10} {'─'*9} {'─'*9} {'─'*7}  {'─'*6}")
    for anio, mes, ing, gas, aho, tasa in filas:
        estado = "✅ Positivo" if tasa > 0 else "❌ Negativo"
        print(f"  {MESES[mes]} {anio}    €{ing:>8,.0f} €{gas:>8,.0f} "
              f"{'+'if aho>=0 else ''}€{aho:>7,.0f}  {tasa:>6.1f}%  {estado}")

    tasas = [r[5] for r in filas]
    meses_pos = sum(1 for t in tasas if t > 0)
    if tasas:
        print(f"\n  Tasa de ahorro promedio  : {sum(tasas)/len(tasas):.1f}%")
        print(f"  Meses con ahorro positivo: {meses_pos}/{len(tasas)}")
        print(f"  Mejor mes                : {max(tasas):.1f}%")
        print(f"  Peor mes                 : {min(tasas):.1f}%")
        print(f"  Nota: Alta tasa porque gastos TC no están incluidos aquí")

    # ══════════════════════════════════════════════════════════════
    # QUERY 8b — Tasa de ahorro real (CC + TC)
    # ══════════════════════════════════════════════════════════════
    sep("8b. Tasa de ahorro real — con gasto TC incluido")

    cur.execute("""
        SELECT
            ing.anio, ing.mes,
            ROUND(ing.ingresos, 0) as ingresos_eur,
            ROUND(COALESCE(gcc.gastos, 0), 0) as gastos_cc_eur,
            ROUND(COALESCE(gtc.gasto_tc, 0), 0) as gastos_tc_eur,
            ROUND(COALESCE(gcc.gastos,0) + COALESCE(gtc.gasto_tc,0), 0) as total_gastos,
            ROUND(ing.ingresos - COALESCE(gcc.gastos,0)
                  - COALESCE(gtc.gasto_tc,0), 0) as ahorro,
            ROUND((ing.ingresos - COALESCE(gcc.gastos,0)
                   - COALESCE(gtc.gasto_tc,0))
                  / ing.ingresos * 100, 1) as tasa_ahorro
        FROM (
            SELECT m.anio, m.mes,
                   SUM(m.abono_clp / t.clp_eur) as ingresos
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.subcategoria = 'ingreso_laboral'
            AND m.abono_clp > 100000
            GROUP BY m.anio, m.mes
        ) ing
        LEFT JOIN (
            SELECT m.anio, m.mes,
                   SUM(m.cargo_clp / t.clp_eur) as gastos
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.categoria_padre NOT IN ('ignorar','transferencias')
            AND m.subcategoria != 'retiro_efectivo'
            AND m.cargo_clp > 0
            GROUP BY m.anio, m.mes
        ) gcc ON ing.anio = gcc.anio AND ing.mes = gcc.mes
        LEFT JOIN (
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
            GROUP BY CAST(strftime('%Y', c.fecha) AS INT),
                     CAST(strftime('%m', c.fecha) AS INT)
        ) gtc ON ing.anio = gtc.anio AND ing.mes = gtc.mes
        ORDER BY ing.anio, ing.mes
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
        print(f"\n  COMPARACIÓN")
        print(f"  ─────────────────────────────────────────────────────")
        print(f"  Sin TC : tasa promedio ~57.9% (solo gastos CC)")
        print(f"  Con TC : tasa promedio ~{sum(tasas)/len(tasas):.1f}% (gastos CC + compras TC)")
        print(f"  La tarjeta absorbía prácticamente todo el margen aparente")

    # ══════════════════════════════════════════════════════════════
    # QUERY 9 — Gasto corriente Madrid vs Las Condes
    # ══════════════════════════════════════════════════════════════
    sep("9. Gasto corriente: Madrid vs Las Condes por categoría")

    cur.execute("""
        SELECT subcategoria,
               ROUND(AVG(mes_eur), 0) as avg_eur_mes
        FROM (
            SELECT m.subcategoria, m.anio, m.mes,
                   SUM(m.cargo_clp / t.clp_eur) as mes_eur
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.categoria_padre IN
                ('alimentacion','transporte','salud_deporte','servicios')
            AND m.subcategoria NOT IN ('seguro_viaje','tramites','retiro_efectivo')
            AND m.cargo_clp > 0
            GROUP BY m.subcategoria, m.anio, m.mes
        )
        GROUP BY subcategoria
        HAVING COUNT(*) >= 3
        ORDER BY avg_eur_mes DESC
    """)
    chile_db = {row[0]: row[1] for row in cur.fetchall()}
    chile = {**chile_db, **CHILE_AJUSTADO}

    cur.execute("""
        SELECT subcategoria, ROUND(SUM(ABS(importe_eur)) / 2.0, 0) as avg_eur_mes
        FROM es_movimientos
        WHERE es_chile = 0 AND tipo = 'cargo'
        AND categoria_padre IN
            ('alimentacion','transporte','salud_deporte','servicios')
        GROUP BY subcategoria
        ORDER BY avg_eur_mes DESC
    """)
    madrid_db = {row[0]: row[1] for row in cur.fetchall()}
    madrid = {**MADRID_AJUSTADO, **{k: v for k, v in madrid_db.items()
                                     if k not in MADRID_AJUSTADO}}

    todas = sorted(set(list(chile.keys()) + list(madrid.keys())))

    print(f"\n  {'Categoría':<25} {'Las Condes':>12} {'Salamanca':>12} {'Dif EUR':>9} {'Dif %':>8}")
    print(f"  {'─'*25} {'─'*12} {'─'*12} {'─'*9} {'─'*8}")

    total_chile = 0
    total_madrid = 0
    for cat in todas:
        c = chile.get(cat, 0)
        m = madrid.get(cat, 0)
        if c == 0 and m == 0:
            continue
        diff    = m - c
        pct     = ((m-c)/c*100) if c > 0 else 0
        signo   = "+" if diff >= 0 else ""
        signo_p = "+" if pct >= 0 else ""
        print(f"  {cat:<25} €{c:>10,.0f} €{m:>10,.0f} "
              f"{signo}€{diff:>7,.0f} {signo_p}{pct:>6.1f}%")
        total_chile  += c
        total_madrid += m

    print(f"  {'─'*25} {'─'*12} {'─'*12} {'─'*9} {'─'*8}")
    diff_total = total_madrid - total_chile
    signo_t = "+" if diff_total >= 0 else "-"
    print(f"  {'TOTAL CORRIENTE':<25} €{total_chile:>10,.0f} €{total_madrid:>10,.0f} "
          f"{signo_t}€{abs(diff_total):>7,.0f} "
          f"{'+'if diff_total>=0 else ''}{(diff_total/total_chile*100):>6.1f}%")

    print(f"""
  CONCLUSIÓN
  ─────────────────────────────────────────────────
  Gasto corriente Chile  : €{total_chile:,.0f}/mes (excl. deuda y retiros)
  Gasto corriente Madrid : €{total_madrid:,.0f}/mes (datos reales + INE)
  Diferencia             : {'+'if diff_total>=0 else ''}€{diff_total:,.0f}/mes
  Nota: precios comparables, sueldos 2x mayores en Madrid
    """)

    conn.close()
    print("="*62)
    print("  Queries ejecutadas correctamente")
    print(f"  Base de datos: {DB_FILE}")
    print("="*62)

if __name__ == "__main__":
    main()
