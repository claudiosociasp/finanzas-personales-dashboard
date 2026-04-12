"""
Análisis de ingresos — Claudio Socias
Fuente: cc_movimientos (Línea de Crédito Santander Chile)

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/analisis_ingresos.py
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_FILE  = str(BASE_DIR / "finanzas.db")

MESES = {
    1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun",
    7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"
}

def separador(titulo=""):
    if titulo:
        print(f"\n{'='*55}")
        print(f"  {titulo}")
        print(f"{'='*55}")
    else:
        print("-"*55)

def main():
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()

    separador("ANÁLISIS DE INGRESOS — CLAUDIO SOCIAS")

    # ── 1. INGRESOS LABORALES POR EMPRESA ─────────────────────────────────────
    separador("Ingresos laborales por empresa")

    empresas = {
        "PricewaterhouseCoopers": "PRICEWATERH",
        "Clínica Lo Arcaya":      "762091712",
    }

    total_laboral = 0
    for empresa, clave in empresas.items():
        cur.execute('''
            SELECT anio, mes, SUM(abono_clp)
            FROM cc_movimientos
            WHERE subcategoria = "ingreso_laboral"
            AND descripcion LIKE ?
            GROUP BY anio, mes
            ORDER BY anio, mes
        ''', (f"%{clave}%",))
        filas = cur.fetchall()

        if not filas:
            continue

        total_empresa = sum(f[2] for f in filas)
        total_laboral += total_empresa
        meses_trabajados = len(filas)

        print(f"\n  {empresa}")
        print(f"  {'─'*40}")
        for anio, mes, monto in filas:
            print(f"    {MESES[mes]} {anio}    ${monto:>14,.0f} CLP")
        print(f"  {'─'*40}")
        print(f"    Total          ${total_empresa:>14,.0f} CLP")
        print(f"    Meses          {meses_trabajados}")
        print(f"    Promedio/mes   ${total_empresa/meses_trabajados:>14,.0f} CLP")

    # Finiquitos y pagos especiales
    separador("Pagos especiales (finiquito, aguinaldo, bonos)")
    cur.execute('''
        SELECT descripcion, abono_clp, anio, mes
        FROM cc_movimientos
        WHERE subcategoria = "ingreso_laboral"
        AND (
            abono_clp < 500000
            OR descripcion LIKE "%REEMBOLSO%"
        )
        AND descripcion NOT LIKE "%792%"
        ORDER BY anio, mes
    ''')
    pagos_esp = cur.fetchall()
    total_esp = 0
    for desc, monto, anio, mes in pagos_esp:
        nombre = desc.strip()
        print(f"  {MESES[mes]} {anio}  ${monto:>12,.0f}  {nombre[:45]}")
        total_esp += monto
    print(f"\n  Total pagos especiales: ${total_esp:,.0f} CLP")

    # Finiquito Arcaya vía TGR
    cur.execute('''
        SELECT SUM(abono_clp)
        FROM cc_movimientos
        WHERE subcategoria = "devolucion_impuesto"
        AND anio = 2024 AND mes = 11
    ''')
    finiquito_tgr = cur.fetchone()[0] or 0
    print(f"  Nov 2024  ${finiquito_tgr:>12,.0f}  Finiquito Arcaya vía TGR")

    # ── 2. CESANTÍA AFC ────────────────────────────────────────────────────────
    separador("Seguro de cesantía AFC")

    cur.execute('''
        SELECT anio, mes, abono_clp
        FROM cc_movimientos
        WHERE subcategoria = "ingreso_cesantia"
        AND abono_clp > 100
        ORDER BY anio, mes
    ''')
    cesantia = cur.fetchall()
    total_cesantia = 0
    for anio, mes, monto in cesantia:
        print(f"  {MESES[mes]} {anio}    ${monto:>14,.0f} CLP")
        total_cesantia += monto
    print(f"  {'─'*40}")
    print(f"  Total AFC       ${total_cesantia:>14,.0f} CLP")
    print(f"  Meses cobrados  {len(cesantia)}")
    if cesantia:
        print(f"  Promedio/mes    ${total_cesantia/len(cesantia):>14,.0f} CLP")

    # ── 3. DEVOLUCIONES DEL ESTADO ────────────────────────────────────────────
    separador("Devoluciones del Estado (SII / TGR)")

    cur.execute('''
        SELECT anio, mes, abono_clp, descripcion
        FROM cc_movimientos
        WHERE subcategoria = "devolucion_impuesto"
        ORDER BY anio, mes
    ''')
    devoluciones = cur.fetchall()
    total_dev = 0
    for anio, mes, monto, desc in devoluciones:
        etiqueta = "Finiquito Arcaya vía TGR" if anio == 2024 and mes == 11 else "Devolución impuestos SII"
        print(f"  {MESES[mes]} {anio}    ${monto:>14,.0f}  {etiqueta}")
        total_dev += monto
    print(f"  {'─'*40}")
    print(f"  Total           ${total_dev:>14,.0f} CLP")

    # ── 4. RESUMEN TOTAL ───────────────────────────────────────────────────────
    separador("Resumen total de ingresos")

    cur.execute('''
        SELECT SUM(abono_clp)
        FROM cc_movimientos
        WHERE subcategoria = "ingreso_laboral"
    ''')
    total_lab = cur.fetchone()[0] or 0

    print(f"  Ingresos laborales      ${total_lab:>14,.0f} CLP")
    print(f"  Cesantía AFC            ${total_cesantia:>14,.0f} CLP")
    print(f"  Devoluciones Estado     ${total_dev:>14,.0f} CLP")
    print(f"  {'─'*45}")
    gran_total = total_lab + total_cesantia + total_dev
    print(f"  TOTAL INGRESOS          ${gran_total:>14,.0f} CLP")

    # ── 5. CONVERSIÓN A EUR ────────────────────────────────────────────────────
    separador("Equivalencia aproximada en EUR")
    # Tipo de cambio promedio referencial CLP/EUR
    TC_PWCH = 950    # ~2023
    TC_ARCAYA = 1050  # ~2024
    TC_ACTUAL = 1100  # ~2025-2026

    cur.execute('''
        SELECT SUM(abono_clp)
        FROM cc_movimientos
        WHERE subcategoria = "ingreso_laboral"
        AND descripcion LIKE "%PRICEWATERH%"
    ''')
    total_pwc = cur.fetchone()[0] or 0

    cur.execute('''
        SELECT SUM(abono_clp)
        FROM cc_movimientos
        WHERE subcategoria = "ingreso_laboral"
        AND descripcion LIKE "%762091712%"
    ''')
    total_arcaya = cur.fetchone()[0] or 0

    print(f"\n  (Tipos de cambio referenciales aproximados)")
    print(f"  PwC 2023           ${total_pwc:>12,.0f} CLP  ≈  €{total_pwc/TC_PWCH:>8,.0f}")
    print(f"  Clínica Arcaya     ${total_arcaya:>12,.0f} CLP  ≈  €{total_arcaya/TC_ARCAYA:>8,.0f}")
    print(f"  Cesantía AFC       ${total_cesantia:>12,.0f} CLP  ≈  €{total_cesantia/TC_ACTUAL:>8,.0f}")
    print(f"  {'─'*50}")
    print(f"  TOTAL              ${gran_total:>12,.0f} CLP  ≈  €{gran_total/TC_ACTUAL:>8,.0f}")

    print(f"\n  Nota: Para comparación precisa con salarios europeos")
    print(f"  usar la API de tipo de cambio histórico (próxima etapa)")

    conn.close()
    print(f"\n{'='*55}")

if __name__ == "__main__":
    main()
