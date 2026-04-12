"""
Tipo de cambio histórico CLP/EUR
Combina dos archivos del Banco Central de Chile:
  - TCB_510_PARIDADES.xlsx → EUR/USD mensual
  - TCB_511_PARIDADES.xlsx → CLP/USD mensual

Fórmula: CLP/EUR = CLP/USD ÷ EUR/USD

Para meses futuros usa la API de exchangerate-api.com automáticamente.

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/tipo_cambio.py
"""

import json
import urllib.request
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
from datetime import date

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent.parent
DB_PATH      = f"sqlite:///{BASE_DIR / 'finanzas.db'}"
ARCHIVO_EUR  = BASE_DIR / "datos_macro" / "TCB_510_PARIDADES.xlsx"
ARCHIVO_CLP  = BASE_DIR / "datos_macro" / "TCB_511_PARIDADES.xlsx"
API_KEY      = "69ea13d5f58da2aba98d0506"


# ── Cargar archivo del Banco Central ──────────────────────────────────────────
def cargar_bcch(ruta: Path, nombre_col: str) -> pd.DataFrame:
    df = pd.read_excel(ruta, header=None, skiprows=2)
    df.columns = ["fecha", nombre_col]
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df[nombre_col] = pd.to_numeric(df[nombre_col], errors="coerce")
    df = df.dropna()
    df["anio"] = df["fecha"].dt.year.astype(int)
    df["mes"]  = df["fecha"].dt.month.astype(int)
    return df[["anio", "mes", nombre_col]]


# ── Obtener tipo de cambio actual desde API ────────────────────────────────────
def obtener_actual_api() -> tuple:
    url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/USD"
    try:
        resp = urllib.request.urlopen(url, timeout=15)
        data = json.loads(resp.read().decode())
        if data.get("result") == "success":
            clp_usd = data["conversion_rates"].get("CLP")
            eur_usd = data["conversion_rates"].get("EUR")
            return clp_usd, eur_usd
    except Exception as e:
        print(f"  Error API: {e}")
    return None, None


# ── Cargar meses ya guardados en DB ───────────────────────────────────────────
def meses_existentes(engine) -> set:
    try:
        df = pd.read_sql("SELECT anio, mes FROM tipo_cambio", engine)
        return set(zip(df["anio"].astype(int), df["mes"].astype(int)))
    except Exception:
        return set()


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    MESES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
             7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

    print("="*55)
    print("Tipo de cambio histórico CLP/EUR")
    print("="*55)

    engine = create_engine(DB_PATH)

    # ── 1. Cargar ambos archivos BCCH ─────────────────────────────────────────
    print("\nCargando archivos del Banco Central de Chile...")
    df_eur = cargar_bcch(ARCHIVO_EUR, "eur_usd")
    df_clp = cargar_bcch(ARCHIVO_CLP, "clp_usd")
    print(f"  EUR/USD: {len(df_eur)} meses")
    print(f"  CLP/USD: {len(df_clp)} meses")

    # ── 2. Cruzar ambas tablas por anio/mes ───────────────────────────────────
    df = pd.merge(df_clp, df_eur, on=["anio", "mes"], how="inner")
    df["clp_eur"] = (df["clp_usd"] / df["eur_usd"]).round(2)
    df["fuente"]  = "BCCH"
    print(f"  Cruce completado: {len(df)} meses con CLP/EUR calculado")

    # ── 3. Ver qué meses faltan en la DB ─────────────────────────────────────
    existentes = meses_existentes(engine)
    print(f"\n  Meses ya en base de datos: {len(existentes)}")

    df_nuevo = df[~df.apply(
        lambda r: (int(r["anio"]), int(r["mes"])) in existentes, axis=1
    )].copy()

    # ── 4. Agregar mes actual desde API si no está ────────────────────────────
    hoy = date.today()
    anio_actual, mes_actual = hoy.year, hoy.month

    if (anio_actual, mes_actual) not in existentes:
        print(f"\n  Consultando API para {MESES[mes_actual]} {anio_actual}...")
        clp_usd, eur_usd = obtener_actual_api()
        if clp_usd and eur_usd:
            fila_actual = pd.DataFrame([{
                "anio":    anio_actual,
                "mes":     mes_actual,
                "clp_usd": round(clp_usd, 4),
                "eur_usd": round(eur_usd, 6),
                "clp_eur": round(clp_usd / eur_usd, 2),
                "fuente":  "API",
            }])
            df_nuevo = pd.concat([df_nuevo, fila_actual], ignore_index=True)
            print(f"  {MESES[mes_actual]} {anio_actual}: "
                  f"CLP/USD={clp_usd:.2f} | "
                  f"EUR/USD={eur_usd:.4f} | "
                  f"CLP/EUR={clp_usd/eur_usd:.2f}")

    # ── 5. Guardar en DB ──────────────────────────────────────────────────────
    if not df_nuevo.empty:
        cols = ["anio", "mes", "clp_usd", "eur_usd", "clp_eur", "fuente"]
        df_nuevo[cols].to_sql(
            "tipo_cambio", engine, if_exists="append", index=False
        )
        print(f"\nGuardados {len(df_nuevo)} registros nuevos")
    else:
        print("\nNo hay registros nuevos que agregar")

    # ── 6. Resumen ────────────────────────────────────────────────────────────
    df_final = pd.read_sql(
        "SELECT anio, mes, clp_usd, eur_usd, clp_eur, fuente "
        "FROM tipo_cambio ORDER BY anio, mes",
        engine
    )

    print(f"\nTabla tipo_cambio: {len(df_final)} meses\n")
    print(f"  {'Mes':<10} {'CLP/USD':>10} {'EUR/USD':>10} {'CLP/EUR':>10}  Fuente")
    print(f"  {'-'*50}")
    for _, r in df_final.iterrows():
        print(f"  {MESES[int(r.mes)]} {int(r.anio)}"
              f"  {r.clp_usd:>10.2f}"
              f"  {r.eur_usd:>10.4f}"
              f"  {r.clp_eur:>10.2f}"
              f"  {r.fuente}")

    # Estadísticas
    print(f"\n  CLP/EUR promedio período : ${df_final['clp_eur'].mean():,.2f}")
    print(f"  CLP/EUR mínimo           : ${df_final['clp_eur'].min():,.2f} "
          f"({MESES[int(df_final.loc[df_final['clp_eur'].idxmin(),'mes'])]} "
          f"{int(df_final.loc[df_final['clp_eur'].idxmin(),'anio'])})")
    print(f"  CLP/EUR máximo           : ${df_final['clp_eur'].max():,.2f} "
          f"({MESES[int(df_final.loc[df_final['clp_eur'].idxmax(),'mes'])]} "
          f"{int(df_final.loc[df_final['clp_eur'].idxmax(),'anio'])})")

    print(f"\nBase de datos: {BASE_DIR / 'finanzas.db'}")
    print("Ejecuta mensualmente para mantener actualizado el tipo de cambio.")


if __name__ == "__main__":
    main()
