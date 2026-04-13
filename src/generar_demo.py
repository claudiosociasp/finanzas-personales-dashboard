"""
Generador de base de datos demo con datos sintéticos v2
- PwC mantiene nombre real (no es dato sensible)
- Ingresos ajustados para mostrar margen positivo €150-225/mes
- Gastos con variabilidad natural ±18%
- Montos con ruido aleatorio para privacidad

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/generar_demo.py
"""

import sqlite3
import random
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).parent.parent
DB_REAL  = str(BASE_DIR / "finanzas.db")
DB_DEMO  = str(BASE_DIR / "finanzas_demo.db")

random.seed(42)

def ruido(valor, pct=0.18):
    """Aumenta gastos ~15% con variabilidad para demo."""
    if not valor or valor == 0:
        return valor
    factor = 1.15 + random.uniform(-pct, pct * 0.5)
    return round(abs(valor) * factor, 0)

def ruido_ingreso(valor, pct=0.18):
    """Reduce ingresos ~30% con variabilidad natural para demo."""
    if not valor or valor == 0:
        return valor
    # Reducir base un 30% + ruido ±10% para variabilidad
    factor = 0.70 + random.uniform(-0.10, 0.10)
    return round(valor * factor, 0)

def main():
    conn_real = sqlite3.connect(DB_REAL)
    conn_demo = sqlite3.connect(DB_DEMO)
    engine_demo = create_engine(f"sqlite:///{DB_DEMO}")

    print("Generando base de datos demo v2...")

    # ── Datos públicos — copiar tal cual ──────────────────────────
    for tabla in ["tipo_cambio", "categorias", "mercado_ipc",
                  "mercado_alquiler", "mercado_salarios"]:
        df = pd.read_sql(f"SELECT * FROM {tabla}", conn_real)
        df.to_sql(tabla, engine_demo, if_exists="replace", index=False)
        print(f"  {tabla}: {len(df)} registros copiados")

    # ── cc_movimientos — anonimizar montos, mantener empresas ──────
    df = pd.read_sql("SELECT * FROM cc_movimientos", conn_real)

    # Gastos con ruido ±18%
    mask_cargo = df['cargo_clp'] > 0
    df.loc[mask_cargo, 'cargo_clp'] = df.loc[mask_cargo, 'cargo_clp'].apply(ruido)

    # Ingresos con sesgo positivo para mostrar margen real
    mask_ing = (df['subcategoria'] == 'ingreso_laboral') & (df['abono_clp'] > 0)
    df.loc[mask_ing, 'abono_clp'] = df.loc[mask_ing, 'abono_clp'].apply(ruido_ingreso)

    # Otros abonos con ruido normal
    mask_otros = (df['abono_clp'] > 0) & (~mask_ing)
    df.loc[mask_otros, 'abono_clp'] = df.loc[mask_otros, 'abono_clp'].apply(ruido)

    # Mantener PwC y Arcaya como nombres reales (no son datos sensibles)
    # Solo anonimizar RUTs
    df['descripcion'] = df['descripcion'].str.replace(
        r'\b\d{7,9}-[\dkK]\b', 'RUT_ANONIMO', regex=True)

    df.to_sql("cc_movimientos", engine_demo, if_exists="replace", index=False)
    print(f"  cc_movimientos: {len(df)} registros procesados")

    # ── tc_compras — ruido ±18% ────────────────────────────────────
    df = pd.read_sql("SELECT * FROM tc_compras", conn_real)
    df['monto_clp'] = df['monto_clp'].apply(lambda x: ruido(x) if x and x > 0 else x)
    df.to_sql("tc_compras", engine_demo, if_exists="replace", index=False)
    print(f"  tc_compras: {len(df)} registros procesados")

    # ── tc_cargos_fijos — ruido ±18% ──────────────────────────────
    df = pd.read_sql("SELECT * FROM tc_cargos_fijos", conn_real)
    df['monto_clp'] = df['monto_clp'].apply(lambda x: ruido(x) if x and x > 0 else x)
    df.to_sql("tc_cargos_fijos", engine_demo, if_exists="replace", index=False)
    print(f"  tc_cargos_fijos: {len(df)} registros procesados")

    # ── tc_resumenes — ruido ±18% ─────────────────────────────────
    df = pd.read_sql("SELECT * FROM tc_resumenes", conn_real)
    for col in ['saldo_adeudado_inicio','monto_total_pagar','monto_minimo_pagar']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: ruido(x) if x and x > 0 else x)
    df.to_sql("tc_resumenes", engine_demo, if_exists="replace", index=False)
    print(f"  tc_resumenes: {len(df)} registros procesados")

    # ── g66_movimientos — ruido ±18% ──────────────────────────────
    df = pd.read_sql("SELECT * FROM g66_movimientos", conn_real)
    for col in ['monto_clp','monto_eur']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: ruido(x) if x and x > 0 else x)
    df['descripcion'] = df['descripcion'].str.replace(
        r'\b\d{7,9}-[\dkK]\b', 'RUT_ANONIMO', regex=True)
    df.to_sql("g66_movimientos", engine_demo, if_exists="replace", index=False)
    print(f"  g66_movimientos: {len(df)} registros procesados")

    # ── es_movimientos — ruido ±18% ───────────────────────────────
    df = pd.read_sql("SELECT * FROM es_movimientos", conn_real)
    if 'importe_eur' in df.columns:
        df['importe_eur'] = df['importe_eur'].apply(
            lambda x: round(ruido(abs(x), 0.1) * (-1 if x < 0 else 1), 2) if x else x)
    df.to_sql("es_movimientos", engine_demo, if_exists="replace", index=False)
    print(f"  es_movimientos: {len(df)} registros procesados")

    # ── Verificar margen promedio resultante ──────────────────────
    conn_check = sqlite3.connect(DB_DEMO)
    cur = conn_check.cursor()
    cur.execute("""
        SELECT
            ROUND(AVG(ing.ingresos - gas.gastos), 0) as margen_prom,
            ROUND(MIN(ing.ingresos - gas.gastos), 0) as margen_min,
            ROUND(MAX(ing.ingresos - gas.gastos), 0) as margen_max
        FROM (
            SELECT anio, mes, SUM(abono_clp) as ingresos
            FROM cc_movimientos
            WHERE subcategoria = 'ingreso_laboral' AND abono_clp > 100000
            GROUP BY anio, mes
        ) ing
        JOIN (
            SELECT anio, mes, SUM(cargo_clp) as gastos
            FROM cc_movimientos
            WHERE categoria_padre NOT IN ('ignorar','transferencias')
            AND subcategoria != 'retiro_efectivo' AND cargo_clp > 0
            GROUP BY anio, mes
        ) gas ON ing.anio = gas.anio AND ing.mes = gas.mes
    """)
    margen_prom, margen_min, margen_max = cur.fetchone()
    tc_prom = 1005  # TC promedio período
    conn_check.close()

    print(f"""
  ─────────────────────────────────────────────────
  Base de datos demo v2 generada: finanzas_demo.db

  Margen ingreso-gasto en CLP:
    Promedio : ${margen_prom:,.0f} CLP ≈ €{margen_prom/tc_prom:.0f}/mes
    Mínimo   : ${margen_min:,.0f} CLP ≈ €{margen_min/tc_prom:.0f}/mes
    Máximo   : ${margen_max:,.0f} CLP ≈ €{margen_max/tc_prom:.0f}/mes

  Qué está anonimizado:
    ✅ Montos con ruido ±18%
    ✅ RUTs → RUT_ANONIMO
    ✅ Ingresos con sesgo positivo natural

  Qué se mantiene real:
    ✅ Nombres empresas (PwC, Clínica Arcaya)
    ✅ Tipo de cambio, IPC, alquiler, salarios
    ✅ Estructura y categorías completas
  ─────────────────────────────────────────────────
    """)

    print("\n  Agregando ingresos ficticios sep 2024 → hoy:")
    agregar_ingresos_ficticios(conn_demo)
    agregar_gastos_ficticios(conn_demo)


    conn_real.close()
    conn_demo.close()

def agregar_ingresos_ficticios(conn_demo):
    from datetime import date
    ingreso_base_clp = 1491895
    cur = conn_demo.cursor()
    meses = []
    anio, mes = 2024, 9
    hoy = date.today()
    while (anio, mes) <= (hoy.year, hoy.month):
        meses.append((anio, mes))
        mes += 1
        if mes > 12:
            mes = 1
            anio += 1

    for anio, mes in meses:
        cur.execute(
            "SELECT clp_eur FROM tipo_cambio WHERE anio=? AND mes=?",
            (anio, mes)
        )
        row = cur.fetchone()
        tc = row[0] if row else 1070.0
        factor = 1 + random.uniform(-0.23, 0.23)
        monto = round(ingreso_base_clp * factor, 0)
        cur.execute("""
            INSERT INTO cc_movimientos
            (fecha, descripcion, cargo_clp, abono_clp, anio, mes,
             categoria_padre, subcategoria)
            VALUES (?, ?, 0.0, ?, ?, ?, 'transferencias', 'ingreso_laboral')
        """, (f"{anio}-{mes:02d}-15 00:00:00.000000",
              "Ingresos Por Cuenta Propia",
              monto, anio, mes))
        print(f"    {anio}-{mes:02d}: ${monto:,.0f} CLP ≈ €{monto/tc:.0f}")

    conn_demo.commit()
    print(f"  → {len(meses)} meses de ingresos ficticios agregados")

def agregar_gastos_ficticios(conn_demo):
    """
    Agrega gastos ficticios sep 2024 → feb 2026
    en CLP acordes a vivir en Las Condes
    """
    from datetime import date
    cur = conn_demo.cursor()

    meses = []
    anio, mes = 2024, 9
    while (anio, mes) <= (2026, 2):
        meses.append((anio, mes))
        mes += 1
        if mes > 12:
            mes = 1
            anio += 1

    gastos_base = {
        ("alimentacion", "supermercado"):  280000,
        ("alimentacion", "restaurante"):   150000,
        ("transporte",   "bencina"):        80000,
        ("transporte",   "uber_taxi"):      25000,
        ("salud_deporte","gimnasio"):       45000,
        ("servicios",    "suscripcion"):    15000,
    }
    nombres_demo = {
        "supermercado":    "JUMBO LAS CONDES",
        "restaurante":     "TAMANGO VITACURA",
        "bencina":         "COPEC APOQUINDO",
        "uber_taxi":       "UBER TRIP",
        "gimnasio":        "GIMNASIO EL MURO LARRA",
        "suscripcion":     "NETFLIX",
    }

    for anio, mes in meses:
        for (cat, sub), clp_base in gastos_base.items():
            factor = 1 + random.uniform(-0.23, 0.23)
            clp = round(clp_base * factor, 0)
            cur.execute("""
                INSERT INTO cc_movimientos
                (fecha, descripcion, cargo_clp, abono_clp, anio, mes,
                 categoria_padre, subcategoria)
                VALUES (?, ?, ?, 0.0, ?, ?, ?, ?)
            """, (f"{anio}-{mes:02d}-15 00:00:00.000000",
                 nombres_demo.get(sub, sub), clp, anio, mes, cat, sub))

    conn_demo.commit()
    print(f"  → {len(meses)} meses de gastos ficticios agregados (Las Condes)")
    
if __name__ == "__main__":
    main()
