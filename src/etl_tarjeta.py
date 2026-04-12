"""
ETL - Extractor de estados de cuenta Santander Chile
Tarjeta de crédito (PDFs)

Estructura esperada:
    ~/Desktop/finanzas_personales/
        tarjeta_credito/   ← PDFs aquí
        cuenta_corriente/
        src/
            etl_tarjeta.py

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/etl_tarjeta.py
"""

import re
import pdfplumber
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent.parent
CARPETA_PDF    = BASE_DIR / "tarjeta_credito"
DB_PATH        = f"sqlite:///{BASE_DIR / 'finanzas.db'}"
TARJETA_PROPIA = "1282"  # cualquier otra tarjeta genera alerta


# ── Categorización ─────────────────────────────────────────────────────────────
CATEGORIAS = {
    "supermercado":    ["UNIMARC", "JUMBO", "LIDER", "TOTTUS", "SANTA ISABEL", "SPID"],
    "bencina":         ["SHELL", "COPEC", "PETROBRAS", "PETRO", "PRONTO"],
    "restaurante":     ["BEER GARDEN", "CAFE", "RESTAURANT", "MIGUELAYO",
                        "OXXO", "PIZZA", "SUSHI", "BAR", "NICOLAS","CURACARIBS"],
    "estacionamiento": ["PARKING", "CENTRAL PARKING", "REPUBLIC PARKING"],
    "salud_seguro":    ["METLIFE", "CLINICA", "FARMACIA", "SALUD"],
    "deuda_cuotas":    ["TRASP A CUOTAS", "CUOTAS DEUDA"],
    "intereses":       ["INTERESES"],
    "impuestos":       ["IMPUESTOS"],
    "traspaso":        ["TRASPASO A DEUDA"],
}

def categorizar(descripcion: str) -> str:
    desc = str(descripcion).upper()
    for categoria, palabras in CATEGORIAS.items():
        if any(p in desc for p in palabras):
            return categoria
    return "otros"


# ── Limpieza de montos ─────────────────────────────────────────────────────────
def limpiar_monto(texto: str) -> float:
    """'$35.000' → 35000.0  |  '$-284.288' → -284288.0"""
    if not texto:
        return 0.0
    # quitar todo excepto dígitos y signo negativo
    limpio = re.sub(r"[^\d\-]", "", str(texto).replace(".", ""))
    try:
        return float(limpio)
    except ValueError:
        return 0.0


# ── Detectar tarjetas ajenas ───────────────────────────────────────────────────
def detectar_tarjetas_externas(texto: str) -> list:
    tarjetas = re.findall(r"MOVIMIENTOS TARJETA XXXX-(\d{4})", texto)
    return [t for t in set(tarjetas) if t != TARJETA_PROPIA]


# ── Extractor de un PDF ────────────────────────────────────────────────────────
def extraer_estado_de_cuenta(ruta_pdf: Path) -> dict:
    nombre       = ruta_pdf.stem
    compras      = []
    cargos_fijos = []
    alertas      = []
    resumen      = {"archivo": nombre}

    with pdfplumber.open(ruta_pdf) as pdf:
        texto_completo = "\n".join(
            page.extract_text() or "" for page in pdf.pages
        )

        # ── Fecha del estado ───────────────────────────────────────────────
        m = re.search(r"FECHA ESTADO DE CUENTA\s+(\d{2}/\d{2}/\d{4})", texto_completo)
        if m:
            resumen["fecha_estado"] = pd.to_datetime(m.group(1), dayfirst=True)

        # ── Período facturado ──────────────────────────────────────────────
        m = re.search(
            r"PERÍODO FACTURADO\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})",
            texto_completo
        )
        if m:
            resumen["periodo_desde"] = pd.to_datetime(m.group(1), dayfirst=True)
            resumen["periodo_hasta"] = pd.to_datetime(m.group(2), dayfirst=True)

        # ── Montos del resumen ─────────────────────────────────────────────
        patrones = {
            "saldo_adeudado_inicio": r"SALDO ADEUDADO INICIO PERÍODO ANTERIOR \$ ([\d\.]+)",
            "monto_total_pagar":     r"MONTO TOTAL FACTURADO A PAGAR \$ ([\d\.]+)",
            "monto_minimo_pagar":    r"MONTO MÍNIMO A PAGAR \$ ([\d\.]+)",
            "saldo_capital_deuda":   r"SALDO CAPITAL\s+CUOTAS\s+.*?\$([\d\.]+)",
        }
        for campo, patron in patrones.items():
            m = re.search(patron, texto_completo, re.DOTALL)
            if m:
                resumen[campo] = limpiar_monto(m.group(1))

        # ── Número de cuota ────────────────────────────────────────────────
        m = re.search(r"(\d{2})/35\s+\$283", texto_completo)
        if m:
            resumen["num_cuota"] = int(m.group(1))

        # ── Alertas tarjetas ajenas ────────────────────────────────────────
        for tarjeta_ext in detectar_tarjetas_externas(texto_completo):
            patron_sec = (
                r"MOVIMIENTOS TARJETA XXXX-" + tarjeta_ext +
                r"(.*?)(?:MOVIMIENTOS TARJETA|2\. PRODUCTOS|$)"
            )
            sec = re.search(patron_sec, texto_completo, re.DOTALL)
            movs = []
            if sec:
                # formato pegado: "12/12/25MONTO CANCELADO $ -4.000"
                movs = re.findall(
                    r"(\d{2}/\d{2}/\d{2})(MONTO CANCELADO)\s*\$\s*([\-\d\.]+)",
                    sec.group(1)
                )
            alertas.append({
                "archivo":     nombre,
                "tarjeta":     tarjeta_ext,
                "movimientos": movs,
            })

        # ── Extraer movimientos del texto completo ─────────────────────────
        # El texto real tiene este formato (fecha pegada a descripción):
        #   "QUILPUE 04/12/25SHELL LOS CARRERA 620 F97 $35.000"
        #   "03/12/25MONTO CANCELADO $ -284.288"
        #   "10/12/25TRASPASO A DEUDA NACIONAL $4.312"

        tarjeta_activa = TARJETA_PROPIA

        for linea in texto_completo.split("\n"):
            linea = linea.strip()
            if not linea:
                continue

            # Cambio de sección de tarjeta
            m_tarj = re.search(r"MOVIMIENTOS TARJETA XXXX-(\d{4})", linea)
            if m_tarj:
                tarjeta_activa = m_tarj.group(1)
                continue

            es_propia = (tarjeta_activa == TARJETA_PROPIA)

            # ── Compras con lugar: "LUGAR DD/MM/YYDESCRIPCIÓN $MONTO"
            # El lugar son palabras en mayúsculas antes de la fecha
            m_compra = re.match(
                r"^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.]{1,25}?)\s+"
                r"(\d{2}/\d{2}/\d{2,4})\s+"
                r"(.+?)\s+"
                r"\$\s*([\d\.]+)$",
                linea
            )
            if m_compra and es_propia:
                lugar       = m_compra.group(1).strip()
                fecha_str   = m_compra.group(2)
                descripcion = m_compra.group(3).strip()
                monto       = limpiar_monto(m_compra.group(4))

                # Saltar encabezados de tabla
                if any(x in descripcion.upper() for x in [
                    "LUGAR DE", "FECHA DE", "DESCRIPCIÓN", "CARGO DEL MES",
                    "VALOR CUOTA", "PERÍODO", "OPERACIÓN"
                ]):
                    continue

                anio  = fecha_str[-4:] if len(fecha_str) == 10 else "20" + fecha_str[-2:]
                fecha = pd.to_datetime(
                    f"{anio}-{fecha_str[3:5]}-{fecha_str[:2]}", errors="coerce"
                )

                compras.append({
                    "fecha":       fecha,
                    "lugar":       lugar,
                    "descripcion": descripcion,
                    "monto_clp":   monto,
                    "tipo":        "compra",
                    "categoria":   categorizar(descripcion),
                    "tarjeta":     tarjeta_activa,
                    "archivo":     nombre,
                })
                continue

            # ── Cargos sin lugar: "DD/MM/YYDESCRIPCIÓN $MONTO"
            m_cargo = re.match(
                r"^(\d{2}/\d{2}/\d{2,4})\s+"
                r"(.+?)\s+"
                r"\$\s*([\-\d\.]+)$",
                linea
            )
            if m_cargo:
                fecha_str   = m_cargo.group(1)
                descripcion = m_cargo.group(2).strip()
                monto_raw   = m_cargo.group(3)

                keywords = [
                    "MONTO CANCELADO", "TRASP A CUOTAS", "TRASPASO A DEUDA",
                    "INTERESES", "IMPUESTOS"
                ]
                if not any(k in descripcion.upper() for k in keywords):
                    continue

                monto = limpiar_monto(monto_raw)
                anio  = fecha_str[-4:] if len(fecha_str) == 10 else "20" + fecha_str[-2:]
                fecha = pd.to_datetime(
                    f"{anio}-{fecha_str[3:5]}-{fecha_str[:2]}", errors="coerce"
                )

                if es_propia:
                    tipo      = "abono" if monto < 0 else "cargo_fijo"
                    categoria = categorizar(descripcion)
                else:
                    tipo      = "abono_externo"
                    categoria = "abono_externo"

                cargos_fijos.append({
                    "fecha":       fecha,
                    "descripcion": descripcion,
                    "monto_clp":   monto,
                    "tipo":        tipo,
                    "categoria":   categoria,
                    "tarjeta":     tarjeta_activa,
                    "archivo":     nombre,
                })

    return {
        "resumen":      resumen,
        "compras":      compras,
        "cargos_fijos": cargos_fijos,
        "alertas":      alertas,
    }


# ── Procesar todos los PDFs ────────────────────────────────────────────────────
def procesar_todos_los_pdfs():
    pdfs = sorted(CARPETA_PDF.glob("*.pdf"))
    if not pdfs:
        print(f"\nNo se encontraron PDFs en: {CARPETA_PDF}")
        return None, None, None, None

    print(f"PDFs encontrados: {len(pdfs)}\n")

    todos_resumenes, todas_compras, todos_cargos, todas_alertas = [], [], [], []

    for pdf in pdfs:
        print(f"  Procesando: {pdf.name}")
        r = extraer_estado_de_cuenta(pdf)
        todos_resumenes.append(r["resumen"])
        todas_compras.extend(r["compras"])
        todos_cargos.extend(r["cargos_fijos"])
        todas_alertas.extend(r["alertas"])

    return (
        pd.DataFrame(todos_resumenes),
        pd.DataFrame(todas_compras)  if todas_compras  else pd.DataFrame(),
        pd.DataFrame(todos_cargos)   if todos_cargos   else pd.DataFrame(),
        todas_alertas,
    )


# ── Alertas ────────────────────────────────────────────────────────────────────
def mostrar_alertas(alertas: list):
    if not alertas:
        return
    print("\n" + "="*55)
    print("ALERTA — Tarjeta desconocida detectada")
    print("="*55)
    for a in alertas:
        print(f"\nArchivo : {a['archivo']}")
        print(f"Tarjeta : XXXX-{a['tarjeta']} (no es tu tarjeta 1282)")
        if a["movimientos"]:
            for fecha, desc, monto in a["movimientos"]:
                print(f"  {fecha}  |  {desc}  |  ${monto}")
        else:
            print("  (movimientos incluidos en el saldo, sin detalle separado)")
    print("\n→ Verifica con Santander si estos movimientos son correctos.")
    print("="*55 + "\n")


# ── Guardar en SQLite ──────────────────────────────────────────────────────────
def guardar_en_db(df_resumenes, df_compras, df_cargos):
    engine = create_engine(DB_PATH)

    df_resumenes.to_sql("tc_resumenes", engine, if_exists="replace", index=False)
    print(f"  tc_resumenes:    {len(df_resumenes)} registros")

    if not df_compras.empty:
        df_compras.to_sql("tc_compras", engine, if_exists="replace", index=False)
        print(f"  tc_compras:      {len(df_compras)} registros")
    else:
        print("  tc_compras:      0 registros (sin compras detectadas)")

    if not df_cargos.empty:
        df_cargos.to_sql("tc_cargos_fijos", engine, if_exists="replace", index=False)
        print(f"  tc_cargos_fijos: {len(df_cargos)} registros")
    else:
        print("  tc_cargos_fijos: 0 registros")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("="*55)
    print("ETL Tarjeta de Crédito — Santander Chile")
    print("="*55)

    df_resumenes, df_compras, df_cargos, alertas = procesar_todos_los_pdfs()

    if df_resumenes is not None:

        mostrar_alertas(alertas)

        print("Guardando en base de datos...")
        guardar_en_db(df_resumenes, df_compras, df_cargos)

        print("\nResumen general:")
        print(f"  Períodos procesados : {len(df_resumenes)}")

        if not df_compras.empty:
            print(f"  Total compras       : {len(df_compras)}")
            print(f"  Gasto total         : ${df_compras['monto_clp'].sum():,.0f} CLP")
            print(f"\nCompras por categoría:")
            resumen_cat = (
                df_compras.groupby("categoria")["monto_clp"]
                .agg(["sum", "count"])
                .sort_values("sum", ascending=False)
            )
            for cat, row in resumen_cat.iterrows():
                print(f"  {cat:<22} ${row['sum']:>12,.0f}  ({int(row['count'])} transacciones)")

        if not df_cargos.empty:
            def suma(cat=None, tipo=None):
                if cat:
                    return df_cargos[df_cargos["categoria"] == cat]["monto_clp"].sum()
                return df_cargos[df_cargos["tipo"] == tipo]["monto_clp"].sum()

            print(f"\nCargos financieros:")
            print(f"  Cuotas deuda        : ${suma(cat='deuda_cuotas'):>12,.0f} CLP")
            print(f"  Intereses           : ${suma(cat='intereses'):>12,.0f} CLP")
            print(f"  Impuestos           : ${suma(cat='impuestos'):>12,.0f} CLP")
            ab_ext = suma(tipo="abono_externo")
            if ab_ext != 0:
                print(f"  Abonos externos     : ${ab_ext:>12,.0f} CLP  (tarjeta ajena)")

        print(f"\nBase de datos: {BASE_DIR / 'finanzas.db'}")