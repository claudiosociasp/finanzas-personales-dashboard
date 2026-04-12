"""
ETL - Global66 (CLP y EUR) + Santander España
Archivos: PDFs de Global66 y XLS del Santander España

Estructura esperada:
    ~/Desktop/finanzas_personales/
        global66/
            clp/   ← PDFs en CLP
            eur/   ← PDFs en EUR
        santander_españa/
            export202645.xls  ← y futuros exports
        src/
            etl_global66_españa.py

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/etl_global66_españa.py
"""

import re
import pdfplumber
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_DIR          = Path(__file__).parent.parent
DB_PATH           = f"sqlite:///{BASE_DIR / 'finanzas.db'}"
CARPETA_G66_CLP   = BASE_DIR / "global66" / "clp"
CARPETA_G66_EUR   = BASE_DIR / "global66" / "eur"
CARPETA_ES        = BASE_DIR / "santander_españa"
TARJETA_ES        = "9772"   # últimos 4 dígitos tarjeta débito España
FILA_HEADER_ES    = 7        # fila donde están los encabezados reales del XLS


# ── Categorización Global66 ────────────────────────────────────────────────────
CATEGORIAS_G66 = {
    "transferencia_enviada": ["Envío a cuenta bancaria", "Envío a"],
    "transferencia_recibida": ["Recibido de"],
    "costo_cambio":          ["Costo tipo de cambio"],
    "conversion_divisas":    ["Conversión de divisas"],
    "comision":              ["Comisión envío", "Comision"],
    "suscripcion":           ["Spotify", "Netflix", "Amazon", "Disney"],
}

def categorizar_g66(descripcion: str) -> str:
    desc = str(descripcion)
    for categoria, palabras in CATEGORIAS_G66.items():
        if any(p.lower() in desc.lower() for p in palabras):
            return categoria
    return "otros"


# ── Categorización Santander España ───────────────────────────────────────────
CATEGORIAS_ES = {
    "supermercado":    ["MERCADONA", "CARREFOUR", "LIDL", "ALDI", "DIA",
                        "UNIMARC", "JUMBO"],
    "restaurante":     ["RESTAURAN", "CAFE", "BAR ", "PIZZA", "SUSHI",
                        "EMPANADA", "PANADERO", "BARBERIA", "MIALCAMPO",
                        "CAFECAMPESINO", "PAMP"],
    "transporte":      ["UBER", "CABIFY", "METRO", "RENFE", "BUS",
                        "TRANSFER T Y T"],
    "suscripcion":     ["SPOTIFY", "NETFLIX", "AMAZON", "DISNEY", "APPLE"],
    "servicios":       ["SUMUP", "MERPAGO", "MERCADOPAGO", "PAYU"],
    "transferencia":   ["TRANSFERENCIA", "BIZUM", "REMESA"],
    "comision_ext":    ["COMISION", "COMISIÓN"],
    "compra_chile":    ["COYHAIQUE", "LAS CONDES", "SANTIAGO", "CHILE"],
}

def categorizar_es(concepto: str) -> str:
    conc = str(concepto).upper()
    for categoria, palabras in CATEGORIAS_ES.items():
        if any(p in conc for p in palabras):
            return categoria
    return "otros"


# ── Limpieza de montos ─────────────────────────────────────────────────────────
def limpiar_monto_clp(texto: str) -> float:
    """'$97,000' → 97000.0"""
    if not texto or str(texto).strip() in ["", "nan"]:
        return 0.0
    limpio = re.sub(r"[^\d\-]", "", str(texto).replace(",", ""))
    try:
        return float(limpio)
    except ValueError:
        return 0.0

def limpiar_monto_eur(texto: str) -> float:
    """'€21.00' o '-11.95' → float"""
    if not texto or str(texto).strip() in ["", "nan"]:
        return 0.0
    limpio = re.sub(r"[€$\s]", "", str(texto)).replace(",", ".")
    try:
        return float(limpio)
    except ValueError:
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL66
# ══════════════════════════════════════════════════════════════════════════════

def extraer_global66_pdf(ruta_pdf: Path, moneda: str) -> list:
    """
    Extrae transacciones de un PDF de Global66.
    moneda: 'CLP' o 'EUR'
    """
    movimientos = []
    nombre = ruta_pdf.stem

    with pdfplumber.open(ruta_pdf) as pdf:
        texto_completo = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # Extraer período del encabezado
    m_desde = re.search(r"Desde:\s+(\d{2}-\w+-\d{4})", texto_completo)
    m_hasta = re.search(r"Hasta:\s+(\d{2}-\w+-\d{4})", texto_completo)

    # Patron de transacción:
    # "2026-01-26 12:14:50 Descripción MOVIMIENTO [TARJETA] DEBITO ABONO SALDO"
    # El texto viene con saltos de línea dentro de la descripción a veces

    # Primero reconstruir líneas completas
    lineas = texto_completo.split("\n")
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()

        # Detectar inicio de transacción por fecha
        m_fecha = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*(.*)", linea)
        if m_fecha:
            fecha_str  = m_fecha.group(1)
            resto      = m_fecha.group(2)

            # Si la descripción continúa en la siguiente línea
            if i + 1 < len(lineas):
                sig = lineas[i + 1].strip()
                # Si la siguiente línea no empieza con fecha ni número de movimiento
                if not re.match(r"^\d{4}-\d{2}-\d{2}", sig) and not re.match(r"^\d{8}", sig):
                    resto = resto + " " + sig
                    i += 1

            # Parsear el resto: DESCRIPCIÓN MOVIMIENTO [TARJETA] DEBITO ABONO SALDO
            # Extraer números al final
            numeros = re.findall(r"[\$€]?([\d,\.]+)", resto)
            movimiento_id = re.search(r"\b(\d{8})\b", resto)
            tarjeta_num   = re.search(r"\b(\d{4})\b(?=\s|$)", resto)

            # Identificar débito y abono según símbolo de moneda
            simbolo = "$" if moneda == "CLP" else "€"
            debito  = 0.0
            abono   = 0.0

            montos_raw = re.findall(rf"{re.escape(simbolo)}([\d,\.]+)", resto)
            if len(montos_raw) >= 2:
                debito = limpiar_monto_clp(montos_raw[0]) if moneda == "CLP" else limpiar_monto_eur(montos_raw[0])
                abono  = limpiar_monto_clp(montos_raw[1]) if moneda == "CLP" else limpiar_monto_eur(montos_raw[1])
            elif len(montos_raw) == 1:
                monto = limpiar_monto_clp(montos_raw[0]) if moneda == "CLP" else limpiar_monto_eur(montos_raw[0])
                # Determinar si es débito o abono por palabras clave
                if any(k in resto for k in ["Envío", "Costo", "Compra", "Comisión"]):
                    debito = monto
                else:
                    abono = monto

            # Descripción limpia
            descripcion = re.sub(r"\d{8}", "", resto)
            descripcion = re.sub(rf"{re.escape(simbolo)}[\d,\.]+", "", descripcion)
            descripcion = re.sub(r"\b\d{4}\b", "", descripcion).strip()
            descripcion = re.sub(r"\s+", " ", descripcion).strip()

            try:
                fecha = pd.to_datetime(fecha_str)
            except Exception:
                fecha = None

            # monto_neto: positivo = ingreso, negativo = gasto
            monto_neto = abono - debito

            movimientos.append({
                "fecha":        fecha,
                "descripcion":  descripcion,
                "debito":       debito,
                "abono":        abono,
                "monto_neto":   monto_neto,
                "moneda":       moneda,
                "tipo":         "abono" if abono > debito else "cargo",
                "categoria":    categorizar_g66(descripcion),
                "archivo":      nombre,
            })

        i += 1

    return movimientos


def procesar_global66():
    movimientos = []

    for moneda, carpeta in [("CLP", CARPETA_G66_CLP), ("EUR", CARPETA_G66_EUR)]:
        pdfs = sorted(carpeta.glob("*.pdf"))
        if not pdfs:
            print(f"  Global66 {moneda}: no se encontraron PDFs en {carpeta}")
            continue
        print(f"  Global66 {moneda}: {len(pdfs)} archivo(s)")
        for pdf in pdfs:
            print(f"    Procesando: {pdf.name}")
            movs = extraer_global66_pdf(pdf, moneda)
            movimientos.extend(movs)
            print(f"    → {len(movs)} transacciones extraídas")

    return pd.DataFrame(movimientos) if movimientos else pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# SANTANDER ESPAÑA
# ══════════════════════════════════════════════════════════════════════════════

def limpiar_concepto_es(concepto: str) -> tuple:
    """
    Limpia el concepto y extrae la comisión si existe.
    'Compra Spotify P40f580f23, Stockholm, Tarjeta 5489010538489772 , Comision 0,00'
    → descripcion limpia + comision float
    """
    texto = str(concepto).strip()

    # Extraer comisión
    m_com = re.search(r"[Cc]omision\s+([\d,\.]+)", texto)
    comision = 0.0
    if m_com:
        comision = limpiar_monto_eur(m_com.group(1).replace(",", "."))
        texto = texto[:m_com.start()].strip().rstrip(",").strip()

    # Limpiar número de tarjeta completo y anonimizado
    texto = re.sub(r"Tarjeta\s+\d{16}", "", texto)
    texto = re.sub(r"Tarj\.\s*:\s*\*\d+", "", texto)
    texto = re.sub(r",\s*$", "", texto).strip()
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto, comision


def extraer_santander_españa(ruta_xls: Path) -> list:
    nombre = ruta_xls.stem
    movimientos = []

    df_raw = pd.read_excel(ruta_xls, header=None)

    # Extraer saldo actual del encabezado
    saldo_actual = None
    for _, row in df_raw.iloc[:FILA_HEADER_ES].iterrows():
        for i, celda in enumerate(row):
            if "Saldo" in str(celda) and i + 1 < len(row):
                val = limpiar_monto_eur(str(row.iloc[i + 1]))
                if val > 0:
                    saldo_actual = val

    # Leer movimientos desde fila FILA_HEADER_ES + 1
    df_mov = df_raw.iloc[FILA_HEADER_ES + 1:].copy()
    df_mov.columns = range(len(df_mov.columns))

    for _, row in df_mov.iterrows():
        fecha_op_raw  = row.iloc[0]
        fecha_val_raw = row.iloc[1]
        concepto_raw  = row.iloc[2]
        importe_raw   = row.iloc[3]
        saldo_raw     = row.iloc[4] if len(row) > 4 else None

        # Saltar filas vacías
        if pd.isna(fecha_op_raw) or pd.isna(concepto_raw):
            continue
        if str(concepto_raw).strip() in ["nan", "CONCEPTO", ""]:
            continue

        # Fechas
        try:
            fecha_op  = pd.to_datetime(str(fecha_op_raw).strip(), dayfirst=True, errors="coerce")
            fecha_val = pd.to_datetime(str(fecha_val_raw).strip(), dayfirst=True, errors="coerce")
        except Exception:
            fecha_op  = None
            fecha_val = None

        # Concepto y comisión
        descripcion, comision = limpiar_concepto_es(str(concepto_raw))

        # Importe (negativo = cargo, positivo = abono)
        importe = limpiar_monto_eur(str(importe_raw))
        saldo   = limpiar_monto_eur(str(saldo_raw)) if saldo_raw else None

        # Detectar si es compra en el extranjero (comisión > 0)
        es_extranjero = comision > 0

        # Detectar si es compra en Chile
        es_chile = any(p in str(concepto_raw).upper() for p in [
            "COYHAIQUE", "LAS CONDES", "SANTIAGO", "CHILE",
            "VITACURA", "PROVIDENCIA", "QUILPUE", "VINA DEL MAR"
        ])

        tipo = "abono" if importe > 0 else "cargo"
        categoria = categorizar_es(str(concepto_raw))

        movimientos.append({
            "fecha_operacion":  fecha_op,
            "fecha_valor":      fecha_val,
            "descripcion":      descripcion,
            "importe_eur":      importe,
            "saldo_eur":        saldo,
            "comision_eur":     comision,
            "tipo":             tipo,
            "categoria":        categoria,
            "es_extranjero":    es_extranjero,
            "es_chile":         es_chile,
            "archivo":          nombre,
        })

    return movimientos


def procesar_santander_españa():
    archivos = sorted(CARPETA_ES.glob("*.xls")) + sorted(CARPETA_ES.glob("*.xlsx"))
    if not archivos:
        print(f"  Santander España: no se encontraron archivos en {CARPETA_ES}")
        return pd.DataFrame()

    print(f"  Santander España: {len(archivos)} archivo(s)")
    movimientos = []
    for archivo in archivos:
        print(f"    Procesando: {archivo.name}")
        movs = extraer_santander_españa(archivo)
        movimientos.extend(movs)
        print(f"    → {len(movs)} movimientos extraídos")

    return pd.DataFrame(movimientos) if movimientos else pd.DataFrame()


# ── Guardar en SQLite ──────────────────────────────────────────────────────────
def guardar_en_db(df_g66, df_es):
    engine = create_engine(DB_PATH)

    if not df_g66.empty:
        df_g66.to_sql("g66_movimientos", engine, if_exists="replace", index=False)
        print(f"  g66_movimientos: {len(df_g66)} registros")
    else:
        print("  g66_movimientos: 0 registros")

    if not df_es.empty:
        df_es.to_sql("es_movimientos", engine, if_exists="replace", index=False)
        print(f"  es_movimientos:  {len(df_es)} registros")
    else:
        print("  es_movimientos:  0 registros")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("="*55)
    print("ETL Global66 + Santander España")
    print("="*55)

    print("\nProcesando Global66...")
    df_g66 = procesar_global66()

    print("\nProcesando Santander España...")
    df_es = procesar_santander_españa()

    print("\nGuardando en base de datos...")
    guardar_en_db(df_g66, df_es)

    # ── Resumen Global66 ──────────────────────────────────────────────────
    if not df_g66.empty:
        print("\nResumen Global66:")
        for moneda in ["CLP", "EUR"]:
            df_m = df_g66[df_g66["moneda"] == moneda]
            if df_m.empty:
                continue
            simbolo = "$" if moneda == "CLP" else "€"
            enviado  = df_m[df_m["tipo"] == "cargo"]["debito"].sum()
            recibido = df_m[df_m["tipo"] == "abono"]["abono"].sum()
            costos   = df_m[df_m["categoria"] == "costo_cambio"]["debito"].sum()
            print(f"\n  {moneda}:")
            print(f"    Recibido        : {simbolo}{recibido:,.2f}")
            print(f"    Enviado         : {simbolo}{enviado:,.2f}")
            print(f"    Costo de cambio : {simbolo}{costos:,.2f}")

    # ── Resumen Santander España ──────────────────────────────────────────
    if not df_es.empty:
        print("\nResumen Santander España:")
        cargos = df_es[df_es["tipo"] == "cargo"]
        abonos = df_es[df_es["tipo"] == "abono"]
        comisiones_ext = df_es["comision_eur"].sum()
        compras_chile  = df_es[df_es["es_chile"] == True]

        print(f"  Total movimientos   : {len(df_es)}")
        print(f"  Total cargos        : €{cargos['importe_eur'].abs().sum():,.2f}")
        print(f"  Total abonos        : €{abonos['importe_eur'].sum():,.2f}")
        print(f"  Comisiones extranjero: €{comisiones_ext:,.2f}")
        if not compras_chile.empty:
            print(f"  Compras desde Chile : {len(compras_chile)} transacciones")

        print(f"\n  Cargos por categoría:")
        resumen_cat = (
            cargos.groupby("categoria")["importe_eur"]
            .agg(lambda x: x.abs().sum())
            .sort_values(ascending=False)
        )
        for cat, total in resumen_cat.items():
            print(f"    {cat:<22} €{total:>10,.2f}")

    print(f"\nBase de datos: {BASE_DIR / 'finanzas.db'}")
