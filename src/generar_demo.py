"""
Generador de base de datos demo con datos sintéticos
Mantiene estructura y proporciones reales pero con valores anonimizados

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/generar_demo.py
    → genera finanzas_demo.db
"""

import sqlite3
import random
import pandas as pd
from pathlib import Path
from datetime import date, timedelta
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).parent.parent
DB_REAL  = str(BASE_DIR / "finanzas.db")
DB_DEMO  = str(BASE_DIR / "finanzas_demo.db")

random.seed(42)  # reproducible

def ruido(valor, pct=0.18):
    """Agrega ruido aleatorio ±pct% a un valor."""
    factor = 1 + random.uniform(-pct, pct)
    return round(valor * factor, 0)

def main():
    conn_real = sqlite3.connect(DB_REAL)
    conn_demo = sqlite3.connect(DB_DEMO)
    engine_demo = create_engine(f"sqlite:///{DB_DEMO}")

    print("Generando base de datos demo...")

    # ── tipo_cambio — dato público, se copia tal cual ──────────────
    df = pd.read_sql("SELECT * FROM tipo_cambio", conn_real)
    df.to_sql("tipo_cambio", engine_demo, if_exists="replace", index=False)
    print(f"  tipo_cambio: {len(df)} registros copiados (dato público)")

    # ── categorias — se copia tal cual (no tiene datos personales) ─
    df = pd.read_sql("SELECT * FROM categorias", conn_real)
    df.to_sql("categorias", engine_demo, if_exists="replace", index=False)
    print(f"  categorias: {len(df)} reglas copiadas")

    # ── mercado_ipc — dato público ─────────────────────────────────
    df = pd.read_sql("SELECT * FROM mercado_ipc", conn_real)
    df.to_sql("mercado_ipc", engine_demo, if_exists="replace", index=False)
    print(f"  mercado_ipc: {len(df)} registros copiados")

    # ── mercado_alquiler — dato público ────────────────────────────
    df = pd.read_sql("SELECT * FROM mercado_alquiler", conn_real)
    df.to_sql("mercado_alquiler", engine_demo, if_exists="replace", index=False)
    print(f"  mercado_alquiler: {len(df)} registros copiados")

    # ── mercado_salarios — dato público ────────────────────────────
    df = pd.read_sql("SELECT * FROM mercado_salarios", conn_real)
    df.to_sql("mercado_salarios", engine_demo, if_exists="replace", index=False)
    print(f"  mercado_salarios: {len(df)} registros copiados")

    # ── cc_movimientos — anonimizar montos y descripciones ─────────
    df = pd.read_sql("SELECT * FROM cc_movimientos", conn_real)

    # Anonimizar montos con ruido
    df['cargo_clp']  = df['cargo_clp'].apply(
        lambda x: ruido(x) if x and x > 0 else x)
    df['abono_clp']  = df['abono_clp'].apply(
        lambda x: ruido(x) if x and x > 0 else x)

    # Anonimizar descripciones sensibles
    mask_ing = df['subcategoria'] == 'ingreso_laboral'
    df.loc[mask_ing & df['descripcion'].str.contains('PRICEWATERH', na=False),
           'descripcion'] = 'EMPRESA_A Remuneraciones'
    df.loc[mask_ing & df['descripcion'].str.contains('762091712', na=False),
           'descripcion'] = 'EMPRESA_B Remuneraciones'

    # Limpiar RUTs y datos identificables
    df['descripcion'] = df['descripcion'].str.replace(
        r'\b\d{7,9}-[\dkK]\b', 'RUT_ANONIMO', regex=True)

    df.to_sql("cc_movimientos", engine_demo, if_exists="replace", index=False)
    print(f"  cc_movimientos: {len(df)} registros anonimizados")

    # ── tc_compras — anonimizar montos ─────────────────────────────
    df = pd.read_sql("SELECT * FROM tc_compras", conn_real)
    df['monto_clp'] = df['monto_clp'].apply(
        lambda x: ruido(x) if x and x > 0 else x)
    df.to_sql("tc_compras", engine_demo, if_exists="replace", index=False)
    print(f"  tc_compras: {len(df)} registros anonimizados")

    # ── tc_cargos_fijos — anonimizar montos ────────────────────────
    df = pd.read_sql("SELECT * FROM tc_cargos_fijos", conn_real)
    df['monto_clp'] = df['monto_clp'].apply(
        lambda x: ruido(x) if x and x > 0 else x)
    df.to_sql("tc_cargos_fijos", engine_demo, if_exists="replace", index=False)
    print(f"  tc_cargos_fijos: {len(df)} registros anonimizados")

    # ── tc_resumenes — anonimizar montos ───────────────────────────
    df = pd.read_sql("SELECT * FROM tc_resumenes", conn_real)
    for col in ['saldo_adeudado_inicio','monto_total_pagar','monto_minimo_pagar']:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: ruido(x) if x and x > 0 else x)
    df.to_sql("tc_resumenes", engine_demo, if_exists="replace", index=False)
    print(f"  tc_resumenes: {len(df)} registros anonimizados")

    # ── g66_movimientos — anonimizar montos ────────────────────────
    df = pd.read_sql("SELECT * FROM g66_movimientos", conn_real)
    for col in ['monto_clp','monto_eur']:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: ruido(x) if x and x > 0 else x)
    df['descripcion'] = df['descripcion'].str.replace(
        r'\b\d{7,9}-[\dkK]\b', 'RUT_ANONIMO', regex=True)
    df.to_sql("g66_movimientos", engine_demo, if_exists="replace", index=False)
    print(f"  g66_movimientos: {len(df)} registros anonimizados")

    # ── es_movimientos — anonimizar montos ─────────────────────────
    df = pd.read_sql("SELECT * FROM es_movimientos", conn_real)
    if 'importe_eur' in df.columns:
        df['importe_eur'] = df['importe_eur'].apply(
            lambda x: round(ruido(x, 0.1), 2) if x else x)
    df.to_sql("es_movimientos", engine_demo, if_exists="replace", index=False)
    print(f"  es_movimientos: {len(df)} registros anonimizados")

    conn_real.close()
    conn_demo.close()

    print(f"""
  ─────────────────────────────────────────────────
  Base de datos demo generada: finanzas_demo.db
  
  Qué está anonimizado:
    ✅ Montos con ruido aleatorio ±18%
    ✅ Nombres de empresas → EMPRESA_A / EMPRESA_B
    ✅ RUTs → RUT_ANONIMO
  
  Qué se copió tal cual (datos públicos):
    ✅ Tipo de cambio CLP/EUR
    ✅ IPC España / Chile
    ✅ Índice alquiler Salamanca
    ✅ Salarios mercado Data/BI Madrid
    ✅ Reglas de categorización
  
  Para usar la demo:
    Cambia DB_FILE en dashboard_app.py:
    DB_FILE = str(BASE_DIR / "finanzas_demo.db")
  ─────────────────────────────────────────────────
    """)

if __name__ == "__main__":
    main()
