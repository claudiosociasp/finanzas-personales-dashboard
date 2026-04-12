"""
Análisis financiero con conversión CLP → EUR
Queries SQL que cruzan movimientos con tipo de cambio histórico

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/analisis_eur.py
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_FILE  = str(BASE_DIR / "finanzas.db")

MESES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
         7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

def separador(titulo=""):
    if titulo:
        print(f"\n{'='*60}")
        print(f"  {titulo}")
        print(f"{'='*60}")
    else:
        print("-"*60)

def main():
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()

    separador("ANÁLISIS FINANCIERO — CLP Y EUR")

    # ══════════════════════════════════════════════════════════════════════════
    # 1. INGRESOS LABORALES EN EUR
    # ══════════════════════════════════════════════════════════════════════════
    separador("1. Ingresos laborales convertidos a EUR")

    cur.execute("""
        SELECT
            m.anio,
            m.mes,
            m.descripcion,
            m.abono_clp,
            t.clp_eur,
            ROUND(m.abono_clp / t.clp_eur, 2) as eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria = 'ingreso_laboral'
        AND m.abono_clp > 100
        ORDER BY m.anio, m.mes
    """)
    filas = cur.fetchall()

    empresa_actual = None
    total_clp = 0
    total_eur = 0

    for anio, mes, desc, clp, tc, eur in filas:
        empresa = "PricewaterhouseCoopers" if "PRICEWATERH" in desc else "Clínica Lo Arcaya"
        if empresa != empresa_actual:
            if empresa_actual:
                print(f"  {'─'*50}")
                print(f"  Subtotal  ${total_clp_emp:>12,.0f} CLP  ≈  €{total_eur_emp:>8,.0f}")
            print(f"\n  {empresa}")
            print(f"  {'─'*50}")
            empresa_actual = empresa
            total_clp_emp = 0
            total_eur_emp = 0

        print(f"  {MESES[mes]} {anio}  "
              f"${clp:>12,.0f} CLP  "
              f"TC:{tc:>8,.0f}  "
              f"≈ €{eur:>8,.2f}")
        total_clp += clp
        total_eur += eur
        total_clp_emp += clp
        total_eur_emp += eur

    print(f"  {'─'*50}")
    print(f"  Subtotal  ${total_clp_emp:>12,.0f} CLP  ≈  €{total_eur_emp:>8,.0f}")
    print(f"\n  TOTAL LABORAL: ${total_clp:>12,.0f} CLP  ≈  €{total_eur:>8,.0f}")

    # Sueldo promedio mensual por empresa
    separador("Sueldo promedio mensual por empresa en EUR")

    cur.execute("""
        SELECT
            CASE WHEN m.descripcion LIKE '%PRICEWATERH%'
                 THEN 'PricewaterhouseCoopers'
                 ELSE 'Clínica Lo Arcaya' END as empresa,
            COUNT(*) as meses,
            ROUND(AVG(m.abono_clp),0) as avg_clp,
            ROUND(AVG(m.abono_clp / t.clp_eur), 0) as avg_eur,
            ROUND(MIN(m.abono_clp / t.clp_eur), 0) as min_eur,
            ROUND(MAX(m.abono_clp / t.clp_eur), 0) as max_eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria = 'ingreso_laboral'
        AND m.abono_clp > 500000
        GROUP BY empresa
        ORDER BY avg_eur DESC
    """)
    for empresa, meses, avg_clp, avg_eur, min_eur, max_eur in cur.fetchall():
        print(f"\n  {empresa}")
        print(f"    Promedio mensual : ${avg_clp:>10,.0f} CLP  ≈  €{avg_eur:>6,.0f}/mes")
        print(f"    Rango EUR        : €{min_eur:,.0f} — €{max_eur:,.0f}")
        print(f"    Anualizado aprox : ≈ €{avg_eur*12:,.0f}/año bruto")

    # ══════════════════════════════════════════════════════════════════════════
    # 2. GASTOS POR CATEGORÍA EN EUR
    # ══════════════════════════════════════════════════════════════════════════
    separador("2. Gastos totales por categoría en EUR (cc_movimientos)")

    cur.execute("""
        SELECT
            m.categoria_padre,
            m.subcategoria,
            COUNT(*) as n,
            ROUND(SUM(m.cargo_clp), 0) as total_clp,
            ROUND(SUM(m.cargo_clp / t.clp_eur), 0) as total_eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.categoria_padre NOT IN ('ignorar', 'transferencias')
        AND m.cargo_clp > 0
        GROUP BY m.categoria_padre, m.subcategoria
        ORDER BY total_eur DESC
    """)
    filas = cur.fetchall()

    padre_actual = None
    total_gasto_eur = 0
    for padre, sub, n, clp, eur in filas:
        if padre != padre_actual:
            print(f"\n  {padre.upper()}")
            padre_actual = padre
        print(f"    └─ {sub:<22} ${clp:>12,.0f}  ≈ €{eur:>7,.0f}  ({n} mov.)")
        total_gasto_eur += eur

    print(f"\n  {'─'*55}")
    print(f"  TOTAL GASTOS: ≈ €{total_gasto_eur:,.0f} EUR en el período")

    # ══════════════════════════════════════════════════════════════════════════
    # 3. GASTO MENSUAL PROMEDIO EN EUR
    # ══════════════════════════════════════════════════════════════════════════
    separador("3. Gasto mensual promedio en EUR por año")

    cur.execute("""
        SELECT
            m.anio,
            COUNT(DISTINCT m.mes) as meses,
            ROUND(SUM(m.cargo_clp), 0) as total_clp,
            ROUND(SUM(m.cargo_clp / t.clp_eur), 0) as total_eur,
            ROUND(SUM(m.cargo_clp / t.clp_eur) /
                  COUNT(DISTINCT m.mes), 0) as promedio_mensual_eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.categoria_padre NOT IN ('ignorar', 'transferencias')
        AND m.cargo_clp > 0
        GROUP BY m.anio
        ORDER BY m.anio
    """)
    for anio, meses, clp, eur, prom in cur.fetchall():
        print(f"  {anio}  {meses} meses  "
              f"${clp:>12,.0f} CLP  "
              f"≈ €{eur:>7,.0f}  "
              f"(€{prom:,.0f}/mes)")

    # ══════════════════════════════════════════════════════════════════════════
    # 4. COSTO REAL DE LA DEUDA EN EUR
    # ══════════════════════════════════════════════════════════════════════════
    separador("4. Costo real de la deuda en EUR")

    cur.execute("""
        SELECT
            m.subcategoria,
            ROUND(SUM(m.cargo_clp), 0) as total_clp,
            ROUND(SUM(m.cargo_clp / t.clp_eur), 0) as total_eur
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria IN ('cuota_lca', 'cuota_tc', 'intereses', 'comision_banco')
        AND m.cargo_clp > 0
        GROUP BY m.subcategoria
        ORDER BY total_eur DESC
    """)
    total_deuda_eur = 0
    for sub, clp, eur in cur.fetchall():
        print(f"  {sub:<22} ${clp:>12,.0f} CLP  ≈ €{eur:>7,.0f}")
        total_deuda_eur += eur
    print(f"  {'─'*50}")
    print(f"  TOTAL COSTO DEUDA    ≈ €{total_deuda_eur:,.0f} EUR")

    # ══════════════════════════════════════════════════════════════════════════
    # 5. COMPARACIÓN SALARIAL CHILE VS ESPAÑA
    # ══════════════════════════════════════════════════════════════════════════
    separador("5. Comparación salarial — Chile vs España")

    # Sueldo promedio Arcaya (excluyendo meses atípicos)
    cur.execute("""
        SELECT ROUND(AVG(m.abono_clp / t.clp_eur), 0)
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria = 'ingreso_laboral'
        AND m.descripcion LIKE '%762091712%'
        AND m.abono_clp BETWEEN 1400000 AND 1600000
    """)
    sueldo_base_eur = cur.fetchone()[0] or 0

    # Sueldo Gerente/Jefe Comercial
    cur.execute("""
        SELECT ROUND(m.abono_clp / t.clp_eur, 0)
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria = 'ingreso_laboral'
        AND m.descripcion LIKE '%762091712%'
        AND m.abono_clp > 2500000
        LIMIT 1
    """)
    sueldo_gerente_eur = cur.fetchone()[0] or 0

    print(f"""
  Tu sueldo base en Clínica Lo Arcaya (2023-2024):
    Chile           : ~$1.500.000 CLP/mes
    En EUR (real)   : ~€{sueldo_base_eur:,.0f}/mes
    Anualizado      : ~€{sueldo_base_eur*12:,.0f}/año

  Tu sueldo como Gerente/Jefe Comercial (jun 2024):
    Chile           : ~$3.000.000 CLP/mes
    En EUR (real)   : ~€{sueldo_gerente_eur:,.0f}/mes
    Anualizado      : ~€{sueldo_gerente_eur*12:,.0f}/año

  Referencia mercado español (sector salud/clínicas, Madrid):
    Jefe Comercial  : €2.500 — €3.500/mes  (€30.000 — €42.000/año)
    Director Comerc.: €3.500 — €5.000/mes  (€42.000 — €60.000/año)

  Barrio Salamanca (Madrid) vs Las Condes (Santiago):
    Ambos son barrios premium de sus ciudades
    Alquiler 1 hab. Salamanca  : €1.200 — €1.800/mes
    Alquiler 1 hab. Las Condes : $700.000 — $1.000.000 CLP
                               ≈ €{700000/1030:,.0f} — €{1000000/1030:,.0f}/mes (TC 2024)

  Conclusión:
    Con sueldo base Arcaya (€{sueldo_base_eur:,.0f}/mes) en España:
    → Cubres el alquiler en Salamanca pero con poco margen
    → Con sueldo de Gerente (€{sueldo_gerente_eur:,.0f}/mes):
    → Cómodo en Salamanca con capacidad de ahorro
    """)

    conn.close()
    print(f"\n{'='*60}")
    print("  Nota: conversiones usando tipo de cambio del mes correspondiente")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
