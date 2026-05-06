"""
ETL - Cartola Línea de Crédito Santander Chile
Archivos Excel (.xlsx)

Estructura esperada:
    ~/Desktop/finanzas_personales/
        cuenta_corriente/   ← todos los Excel aquí
        src/
            etl_cuenta.py

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/etl_cuenta.py
"""

import re
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent.parent
CARPETA_XLS  = BASE_DIR / "cuenta_corriente"
DB_PATH      = f"sqlite:///{BASE_DIR / 'finanzas.db'}"
FILA_HEADER  = 20   # fila donde están los encabezados reales de la tabla


# ── Categorización ─────────────────────────────────────────────────────────────
CATEGORIAS = {
    "supermercado":    ["UNIMARC", "JUMBO", "LIDER", "TOTTUS", "SANTA ISABEL",
                        "SUPERMERCADO"],
    "bencina":         ["SHELL", "COPEC", "PETROBRAS", "PETRO", "PRONTO"],
    "restaurante":     ["BEER GARDEN", "CAFE", "RESTAURANT", "MIGUELAYO",
                        "OXXO", "PIZZA", "SUSHI", "BAR", "LICORERIA",
                        "LICORERA", "CHILEDRINK"],
    "estacionamiento": ["PARKING", "ESTACIONAMIENTO"],
    "salud_seguro":    ["METLIFE", "CLINICA", "FARMACIA", "SALUD", "ISAPRE"],
    "transporte":      ["METRO", "BIP", "UBER", "CABIFY", "TAXI", "BUS"],
    "servicios_basicos": ["ENTEL", "MOVISTAR", "VTR", "CLARO", "INTERNET",
                          "AGUA", "LUZ", "GAS", "ELECTRICIDAD"],
    "transferencia":   ["TRASPASO", "TRANSFERENCIA", "TRANSFER"],
    "cuota_deuda":     ["AMORTIZACIÓN", "AMORTIZACION", "LCA"],
    "intereses":       ["INTERESES", "INTERÉS"],
    "impuestos":       ["IMPUESTO", "TIMBRE"],
    "comisiones":      ["COMISION", "COMISIÓN", "MANTENCIÓN", "MANTENCION"],
    "comercio":        ["COMPRA NACIONAL", "COMPRA INTERN", "NP PAYU",
                        "PAYU", "MERCADOPAGO", "WEBPAY"],
}

def categorizar(descripcion: str) -> str:
    desc = str(descripcion).upper()
    for categoria, palabras in CATEGORIAS.items():
        if any(p in desc for p in palabras):
            return categoria
    return "otros"


# ── Limpieza de montos ─────────────────────────────────────────────────────────
def limpiar_monto(valor) -> float:
    if pd.isna(valor) or valor == "" or valor is None:
        return 0.0
    texto = str(valor).replace("$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(texto)
    except ValueError:
        return 0.0


# ── Extraer año desde nombre de archivo ───────────────────────────────────────
def extraer_anio_mes(nombre: str) -> tuple:
    """
    'Cartola Línea Crédito - Abril 2025' → (2025, 4)
    """
    meses = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
    }
    nombre_lower = nombre.lower()
    anio_match = re.search(r"(\d{4})", nombre)
    anio = int(anio_match.group(1)) if anio_match else None
    mes = None
    for nombre_mes, num_mes in meses.items():
        if nombre_mes in nombre_lower:
            mes = num_mes
            break
    return anio, mes


# ── Extraer resumen del encabezado del Excel ───────────────────────────────────
def extraer_resumen(df_raw: pd.DataFrame, nombre: str, anio: int, mes: int) -> dict:
    """
    Lee las filas de encabezado del banco (0-19) para extraer
    saldos, comisiones y datos del período.
    """
    resumen = {"archivo": nombre, "anio": anio, "mes": mes}

    def buscar_valor(fila, col_etiqueta, col_valor):
        """Busca una etiqueta en col_etiqueta y devuelve el valor de col_valor."""
        for _, row in df_raw.iterrows():
            celda = str(row.iloc[col_etiqueta]).strip()
            if celda in fila:
                return limpiar_monto(row.iloc[col_valor])
        return None

    # Recorrer filas del encabezado buscando campos clave
    for _, row in df_raw.iloc[:FILA_HEADER].iterrows():
        for i, celda in enumerate(row):
            celda_str = str(celda).strip()

            if "Saldo inicial" in celda_str:
                resumen["saldo_inicial"] = limpiar_monto(row.iloc[i+1] if i+1 < len(row) else None)
            elif "Saldo final" in celda_str:
                resumen["saldo_final"] = limpiar_monto(row.iloc[i+1] if i+1 < len(row) else None)
            elif "Otros abonos" in celda_str:
                resumen["total_abonos"] = limpiar_monto(row.iloc[i+1] if i+1 < len(row) else None)
            elif "Otros cargos" in celda_str:
                resumen["total_cargos"] = limpiar_monto(row.iloc[i+1] if i+1 < len(row) else None)
            elif "Comisiones" in celda_str:
                resumen["comisiones"] = limpiar_monto(row.iloc[i+1] if i+1 < len(row) else None)
            elif "Impuestos" in celda_str and "comis" not in celda_str.lower():
                resumen["impuestos"] = limpiar_monto(row.iloc[i+1] if i+1 < len(row) else None)
            elif "Cupo aprobado" in celda_str:
                resumen["cupo_aprobado"] = limpiar_monto(row.iloc[i+1] if i+1 < len(row) else None)
            elif "Monto utilizado" in celda_str:
                resumen["monto_utilizado"] = limpiar_monto(row.iloc[i+1] if i+1 < len(row) else None)
            elif "Saldo disponible" in celda_str:
                resumen["saldo_disponible"] = limpiar_monto(row.iloc[i+1] if i+1 < len(row) else None)

    return resumen


# ── Extraer movimientos ────────────────────────────────────────────────────────
def extraer_movimientos(df_raw: pd.DataFrame, nombre: str, anio: int, mes: int) -> list:
    """
    Lee desde la fila FILA_HEADER+1 en adelante.
    Columnas: FECHA | SUCURSAL | DESCRIPCIÓN | N°DOC | CARGOS | ABONOS | SALDO
    """
    movimientos = []

    # Los datos reales empiezan en FILA_HEADER + 1
    df_mov = df_raw.iloc[FILA_HEADER + 1:].copy()
    df_mov.columns = range(len(df_mov.columns))

    for _, row in df_mov.iterrows():
        fecha_raw   = row.iloc[0]
        sucursal    = str(row.iloc[1]).strip() if not pd.isna(row.iloc[1]) else ""
        descripcion = str(row.iloc[2]).strip() if not pd.isna(row.iloc[2]) else ""
        cargo       = limpiar_monto(row.iloc[4])
        abono       = limpiar_monto(row.iloc[5])
        saldo       = limpiar_monto(row.iloc[6]) if len(row) > 6 else 0.0

        # Saltar filas vacías o sin descripción
        if not descripcion or descripcion in ["nan", "NaN", "DESCRIPCIÓN"]:
            continue
        # Saltar filas que son totales o encabezados repetidos
        if any(x in descripcion.upper() for x in [
            "DETALLE DE MOVIMIENTOS", "SALDOS DIARIOS", "FECHA", "INFORMACIÓN"
        ]):
            continue

        # Construir fecha completa: el Excel trae "DD/MM" sin año
        fecha = None
        fecha_str = str(fecha_raw).strip()
        if re.match(r"\d{1,2}/\d{1,2}", fecha_str):
            dia, mes_num = fecha_str.split("/")[:2]
            try:
                fecha = pd.to_datetime(
                    f"{anio}-{int(mes_num):02d}-{int(dia):02d}", errors="coerce"
                )
            except Exception:
                fecha = None

        # monto_clp: positivo = abono (ingreso), negativo = cargo (gasto)
        monto_clp = abono - cargo if (abono > 0 or cargo > 0) else 0.0

        movimientos.append({
            "fecha":       fecha,
            "sucursal":    sucursal,
            "descripcion": descripcion,
            "cargo_clp":   cargo,
            "abono_clp":   abono,
            "monto_clp":   monto_clp,
            "saldo_clp":   saldo,
            "tipo":        "abono" if abono > 0 else "cargo",
            "categoria":   categorizar(descripcion),
            "anio":        anio,
            "mes":         mes,
            "archivo":     nombre,
        })

    return movimientos


# ── Procesar todos los Excel ───────────────────────────────────────────────────
def procesar_todos_los_excel():
    archivos = sorted(CARPETA_XLS.glob("*.xlsx"))
    if not archivos:
        print(f"\nNo se encontraron archivos en: {CARPETA_XLS}")
        return None, None

    print(f"Archivos encontrados: {len(archivos)}\n")

    todos_resumenes  = []
    todos_movimientos = []

    for archivo in archivos:
        nombre = archivo.stem
        anio, mes = extraer_anio_mes(nombre)

        if not anio or not mes:
            print(f"  OMITIDO (no se pudo extraer fecha): {nombre}")
            continue

        print(f"  Procesando: {nombre}")

        df_raw = pd.read_excel(archivo, header=None)

        resumen = extraer_resumen(df_raw, nombre, anio, mes)
        movs    = extraer_movimientos(df_raw, nombre, anio, mes)

        todos_resumenes.append(resumen)
        todos_movimientos.extend(movs)

    df_resumenes   = pd.DataFrame(todos_resumenes)
    df_movimientos = pd.DataFrame(todos_movimientos) if todos_movimientos else pd.DataFrame()

    return df_resumenes, df_movimientos


# ── Guardar en SQLite ──────────────────────────────────────────────────────────
def guardar_en_db(df_resumenes, df_movimientos):
    engine = create_engine(DB_PATH)

    df_resumenes.to_sql("cc_resumenes", engine, if_exists="replace", index=False)
    print(f"  cc_resumenes:    {len(df_resumenes)} registros")

    if not df_movimientos.empty:
        df_movimientos.to_sql("cc_movimientos", engine, if_exists="replace", index=False)
        print(f"  cc_movimientos:  {len(df_movimientos)} registros")
    else:
        print("  cc_movimientos:  0 registros")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("="*55)
    print("ETL Cuenta Corriente — Santander Chile")
    print("="*55)

    df_resumenes, df_movimientos = procesar_todos_los_excel()

    if df_resumenes is not None:

        print("\nGuardando en base de datos...")
        guardar_en_db(df_resumenes, df_movimientos)

        print("\nResumen general:")
        print(f"  Períodos procesados  : {len(df_resumenes)}")

        if not df_movimientos.empty:
            cargos = df_movimientos[df_movimientos["tipo"] == "cargo"]
            abonos = df_movimientos[df_movimientos["tipo"] == "abono"]

            print(f"  Total movimientos    : {len(df_movimientos)}")
            print(f"  Total cargos         : {len(cargos)}  →  ${cargos['cargo_clp'].sum():,.0f} CLP")
            print(f"  Total abonos         : {len(abonos)}  →  ${abonos['abono_clp'].sum():,.0f} CLP")

            print(f"\nCargos por categoría:")
            resumen_cat = (
                cargos.groupby("categoria")["cargo_clp"]
                .agg(["sum", "count"])
                .sort_values("sum", ascending=False)
            )
            for cat, row in resumen_cat.iterrows():
                print(f"  {cat:<22} ${row['sum']:>14,.0f}  ({int(row['count'])} movimientos)")

        if "comisiones" in df_resumenes.columns:
            total_comisiones = df_resumenes["comisiones"].sum()
            print(f"\nComisiones totales pagadas: ${total_comisiones:,.0f} CLP")

        print(f"\nBase de datos: {BASE_DIR / 'finanzas.db'}")
        print(f"\nBase de datos: {BASE_DIR / 'finanzas.db'}")
        
        # Eliminar duplicados
        import sqlite3
        conn_dedup = sqlite3.connect(str(BASE_DIR / 'finanzas.db'))
        cur = conn_dedup.cursor()
        cur.execute('''
            DELETE FROM cc_movimientos
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM cc_movimientos
                GROUP BY fecha, descripcion, cargo_clp, abono_clp
            )
        ''')
        conn_dedup.commit()
        print(f"  Duplicados eliminados: {cur.rowcount}")
        conn_dedup.close()