"""
Recategorizador unificado — actualiza todas las tablas de movimientos
usando las palabras clave definidas en la tabla 'categorias'.

Ejecutar cada vez que:
    - Agregues nuevos archivos a las carpetas
    - Modifiques palabras clave en categorias.py
    - Quieras corregir categorías incorrectas

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/recategorizar.py
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_FILE  = str(BASE_DIR / "finanzas.db")

# Separadores y ruido del Excel — se eliminan del análisis
IGNORAR = [
    "**************************************************",
    "DESCRIPCIÓN",
    "DETALLE DE MOVIMIENTOS",
    "SALDOS DIARIOS",
]


def cargar_categorias(conn) -> list:
    cur = conn.cursor()
    cur.execute("SELECT categoria_padre, subcategoria, palabra_clave, fuente FROM categorias")
    return cur.fetchall()


def categorizar(descripcion: str, reglas: list, fuente_filtro: str) -> tuple:
    """
    Retorna (categoria_padre, subcategoria).
    Separadores se marcan como ignorar/separador para excluirlos del análisis.
    Prioriza reglas específicas de la fuente sobre las de 'todas'.
    """
    desc_upper = str(descripcion).upper().strip()

    # Detectar separadores — se excluyen del análisis
    if any(ig.upper() in desc_upper for ig in IGNORAR):
        return "ignorar", "separador"

    # Buscar coincidencia — primero fuente específica, luego 'todas'
    for fuente_prio in [fuente_filtro, "todas"]:
        for padre, sub, palabra, fuente in reglas:
            if fuente == fuente_prio:
                if palabra.upper() in desc_upper:
                    return padre, sub

    return "otros", "sin_clasificar"


def recategorizar_tabla(conn, tabla: str, col_descripcion: str,
                        col_padre: str, col_sub: str,
                        fuente: str, reglas: list) -> int:
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,))
    if not cur.fetchone():
        print(f"  Tabla '{tabla}' no encontrada, omitiendo.")
        return 0

    cur.execute(f"PRAGMA table_info({tabla})")
    columnas = [row[1] for row in cur.fetchall()]

    if col_padre not in columnas:
        cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {col_padre} TEXT")
    if col_sub not in columnas:
        cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {col_sub} TEXT")

    cur.execute(f"SELECT rowid, {col_descripcion} FROM {tabla}")
    registros = cur.fetchall()

    actualizados = 0
    for rowid, descripcion in registros:
        padre, sub = categorizar(descripcion or "", reglas, fuente)
        cur.execute(
            f"UPDATE {tabla} SET {col_padre}=?, {col_sub}=? WHERE rowid=?",
            (padre, sub, rowid)
        )
        actualizados += 1

    conn.commit()
    return actualizados


def main():
    print("="*55)
    print("Recategorizador unificado")
    print("="*55)

    conn = sqlite3.connect(DB_FILE)
    reglas = cargar_categorias(conn)
    print(f"\nReglas cargadas: {len(reglas)} palabras clave\n")

    tablas = [
        ("tc_compras",      "descripcion", "categoria_padre", "subcategoria", "chile"),
        ("tc_cargos_fijos", "descripcion", "categoria_padre", "subcategoria", "chile"),
        ("cc_movimientos",  "descripcion", "categoria_padre", "subcategoria", "chile"),
        ("g66_movimientos", "descripcion", "categoria_padre", "subcategoria", "global66"),
        ("es_movimientos",  "descripcion", "categoria_padre", "subcategoria", "españa"),
    ]

    total = 0
    for tabla, col_desc, col_padre, col_sub, fuente in tablas:
        n = recategorizar_tabla(conn, tabla, col_desc, col_padre, col_sub, fuente, reglas)
        print(f"  {tabla:<20} {n:>5} registros actualizados")
        total += n

    conn.close()
    print(f"\nTotal actualizados: {total} registros")
    print("\nVerificando resultados...")
    verificar_resultados()


def verificar_resultados():
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()

    # Configuración: (tabla, col_monto, moneda, incluir_abonos)
    tablas_verificar = [
        ("tc_compras",      "monto_clp",   "CLP", False),
        ("cc_movimientos",  "cargo_clp",   "CLP", True),
        ("es_movimientos",  "importe_eur", "EUR", True),
    ]

    print()
    for tabla, col_monto, moneda, incluir_abonos in tablas_verificar:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,))
        if not cur.fetchone():
            continue

        # Excluir separadores del análisis
        cur.execute(f"""
            SELECT categoria_padre, subcategoria,
                   COUNT(*) as n,
                   ROUND(SUM(ABS({col_monto})), 0) as total
            FROM {tabla}
            WHERE categoria_padre != 'ignorar'
            GROUP BY categoria_padre, subcategoria
            ORDER BY categoria_padre, total DESC
        """)
        filas = cur.fetchall()
        if not filas:
            continue

        simbolo = "€" if moneda == "EUR" else "$"
        print(f"  [{tabla}]")
        padre_actual = None
        for padre, sub, n, total in filas:
            if padre != padre_actual:
                print(f"    {padre}")
                padre_actual = padre
            print(f"      └─ {sub:<25} {simbolo}{total or 0:>14,.0f}  ({n} mov.)")
        print()

    # Pendientes reales (excluye separadores)
    print("  Pendientes de clasificar (sin_clasificar):")
    for tabla, col_monto, moneda, _ in tablas_verificar:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,))
        if not cur.fetchone():
            continue
        cur.execute(f"""
            SELECT COUNT(*), ROUND(SUM(ABS({col_monto})), 0)
            FROM {tabla}
            WHERE subcategoria = 'sin_clasificar'
        """)
        n, total = cur.fetchone()
        if n and n > 0:
            simbolo = "€" if moneda == "EUR" else "$"
            print(f"    {tabla:<22} {n:>4} registros  →  {simbolo}{total or 0:,.0f}")

    # Separadores ignorados (informativo)
    print("\n  Separadores excluidos del análisis:")
    for tabla, _, _, _ in tablas_verificar:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,))
        if not cur.fetchone():
            continue
        cur.execute(f"""
            SELECT COUNT(*) FROM {tabla}
            WHERE categoria_padre = 'ignorar'
        """)
        n = cur.fetchone()[0]
        if n:
            print(f"    {tabla:<22} {n:>4} filas ignoradas")

    conn.close()
    print(f"\nBase de datos: {DB_FILE}")
    print("\nPara agregar palabras clave: edita src/categorias.py y vuelve a ejecutar ambos scripts.")


if __name__ == "__main__":
    main()
