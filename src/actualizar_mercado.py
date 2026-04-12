"""
Actualizador automático de datos de mercado
Actualiza en finanzas.db:
  - mercado_ipc    : IPC España (mensual) + IPC Chile (anual)
  - mercado_alquiler: Índice alquiler Salamanca y Madrid (INE España)
  - mercado_salarios: Rangos salariales Data/BI Madrid (via API Claude)

Fuentes:
  - IPC España  : INE España (servicios.ine.es)
  - IPC Chile   : World Bank API
  - Alquiler    : INE España Índice Precios Vivienda Alquiler
  - Salarios    : API Claude (búsqueda automática)

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/actualizar_mercado.py

Frecuencia recomendada: mensual (junto con tipo_cambio.py)
"""

import json
import time
import urllib.request
import sqlite3
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
from datetime import date, datetime

BASE_DIR  = Path(__file__).parent.parent
DB_FILE   = str(BASE_DIR / "finanzas.db")
DB_PATH   = f"sqlite:///{BASE_DIR / 'finanzas.db'}"

MESES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
         7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

def separador(titulo):
    print(f"\n{'='*58}")
    print(f"  {titulo}")
    print(f"{'='*58}")


# ── 1. IPC ESPAÑA (INE) ────────────────────────────────────────────────────────
def obtener_ipc_espana() -> list:
    """Obtiene IPC España mensual desde INE — variación anual."""
    url = "https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/IPC251856?nult=24"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read().decode("utf-8"))

    registros = []
    for d in data.get("Data", []):
        anyo   = d.get("Anyo")
        periodo = d.get("Periodo", {})
        mes    = int(periodo.get("Mes_inicio", 0)) if periodo else 0
        valor  = d.get("Valor")
        if anyo and mes and valor is not None:
            registros.append({
                "pais":   "España",
                "anio":   anyo,
                "mes":    mes,
                "ipc_variacion_anual": round(valor, 2),
                "fuente": "INE_ES",
                "fecha_actualizacion": date.today().isoformat(),
            })
    return registros


# ── 2. IPC CHILE (mindicador.cl → BCCh) ───────────────────────────────────────
def obtener_ipc_chile() -> list:
    """
    Obtiene IPC Chile variación mensual desde mindicador.cl.
    Fuente original: Banco Central de Chile.
    Cubre 2023 en adelante — descarga año por año.
    """
    anio_actual = date.today().year
    registros   = []

    for anio in range(2023, anio_actual + 1):
        url = f"https://mindicador.cl/api/ipc/{anio}"
        try:
            req  = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("serie", []):
                fecha = item.get("fecha", "")
                valor = item.get("valor")
                if fecha and valor is not None:
                    # fecha viene como "2025-03-01T03:00:00.000Z"
                    mes = int(fecha[5:7])
                    registros.append({
                        "pais":                "Chile",
                        "anio":                anio,
                        "mes":                 mes,
                        "ipc_variacion_mensual": round(float(valor), 2),
                        "fuente":              "mindicador_BCCh",
                        "fecha_actualizacion": date.today().isoformat(),
                    })
            time.sleep(0.3)
        except Exception as e:
            print(f"    Error IPC Chile {anio}: {e}")

    return registros


# ── 3. ÍNDICE ALQUILER SALAMANCA (INE España) ──────────────────────────────────
def obtener_indice_alquiler() -> list:
    """
    Obtiene índice de precios de alquiler para Salamanca y Madrid desde INE.
    Series:
        IPVA8623 → Salamanca. Índice. Total
        IPVA9850 → Salamanca. Índice. Nuevo contrato
        IPVA8774 → Madrid. Índice. Total
    Base 2015 = 100. Dato anual con ~1 año de rezago.
    """
    series = {
        "IPVA8623": ("Salamanca", "total"),
        "IPVA9850": ("Salamanca", "nuevo_contrato"),
        "IPVA8774": ("Madrid",    "total"),
    }

    registros = []
    for cod, (zona, tipo) in series.items():
        url = f"https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/{cod}?nult=5"
        try:
            req  = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode("utf-8"))
            for d in data.get("Data", []):
                anyo  = d.get("Anyo")
                valor = d.get("Valor")
                if anyo and valor is not None:
                    registros.append({
                        "zona":              zona,
                        "tipo_contrato":     tipo,
                        "anio":              anyo,
                        "indice_base2015":   round(valor, 3),
                        "fuente":            f"INE_ES_{cod}",
                        "fecha_actualizacion": date.today().isoformat(),
                    })
            time.sleep(0.3)
        except Exception as e:
            print(f"    Error {cod}: {e}")

    return registros


# ── 4. SALARIOS MERCADO DATA/BI MADRID ────────────────────────────────────────
# Fuente: Glassdoor España, LinkedIn Salary, Tecnoempleo, Estudio Remuneración
#         Tech 2025. Actualizar manualmente una vez al año (abril aprox.)
# Última revisión: Abril 2026
SALARIOS_MERCADO = [
    {
        "nivel":            "junior",
        "descripcion":      "Data Analyst <3 años, Power BI + SQL",
        "salario_min":      22000,
        "salario_max":      28000,
        "neto_mensual_min": 1400,
        "neto_mensual_max": 1800,
    },
    {
        "nivel":            "mid_senior",
        "descripcion":      "Data Analyst 3-5 años, Power BI + SQL + Python",
        "salario_min":      30000,
        "salario_max":      38000,
        "neto_mensual_min": 1800,
        "neto_mensual_max": 2200,
    },
    {
        "nivel":            "senior",
        "descripcion":      "BI Analyst +5 años, multinacional, BI + negocio",
        "salario_min":      38000,
        "salario_max":      46000,
        "neto_mensual_min": 2200,
        "neto_mensual_max": 2700,
    },
    {
        "nivel":            "senior_plus",
        "descripcion":      "BI Senior + Python consolidado + certificaciones",
        "salario_min":      46000,
        "salario_max":      55000,
        "neto_mensual_min": 2700,
        "neto_mensual_max": 3200,
    },
]


def obtener_salarios() -> list:
    """
    Devuelve rangos salariales Data/BI Madrid.
    Actualizar SALARIOS_MERCADO manualmente una vez al año.
    Próxima revisión recomendada: Abril 2027.
    """
    hoy = date.today().isoformat()
    registros = []
    for perfil in SALARIOS_MERCADO:
        registros.append({
            **perfil,
            "ciudad":              "Madrid",
            "fuente":              "Glassdoor/LinkedIn/Tecnoempleo 2025",
            "fecha_actualizacion": hoy,
        })
    return registros


def salarios_desactualizados(conn) -> bool:
    """Retorna True si los salarios tienen más de 365 días o no existen."""
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT MIN(fecha_actualizacion) FROM mercado_salarios
        """)
        fecha_str = cur.fetchone()[0]
        if not fecha_str:
            return True
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        return (date.today() - fecha).days > 365
    except Exception:
        return True


# ── 5. GUARDAR EN DB ──────────────────────────────────────────────────────────
def meses_existentes_ipc(conn, pais) -> set:
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT anio, mes FROM mercado_ipc WHERE pais=?", (pais,)
        )
        return set((r[0], r[1]) for r in cur.fetchall())
    except Exception:
        return set()


def anios_existentes_alquiler(conn, zona, tipo) -> set:
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT anio FROM mercado_alquiler WHERE zona=? AND tipo_contrato=?",
            (zona, tipo)
        )
        return set(r[0] for r in cur.fetchall())
    except Exception:
        return set()


def guardar_tabla(df, tabla, engine, if_exists="append"):
    df.to_sql(tabla, engine, if_exists=if_exists, index=False)


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("="*58)
    print("  Actualizador de datos de mercado")
    print("="*58)
    print(f"  Fecha: {date.today().isoformat()}")

    engine = create_engine(DB_PATH)
    conn   = sqlite3.connect(DB_FILE)

    # ── IPC España ─────────────────────────────────────────────────
    separador("1. IPC España (INE)")
    try:
        registros_es = obtener_ipc_espana()
        existentes   = meses_existentes_ipc(conn, "España")
        nuevos = [r for r in registros_es
                  if (r["anio"], r["mes"]) not in existentes]
        if nuevos:
            pd.DataFrame(nuevos).to_sql(
                "mercado_ipc", engine, if_exists="append", index=False
            )
            print(f"  Guardados {len(nuevos)} meses nuevos de IPC España")
            for r in nuevos[-3:]:
                print(f"    {MESES[r['mes']]} {r['anio']}: "
                      f"{r['ipc_variacion_anual']}% var. anual")
        else:
            print("  IPC España ya actualizado")
    except Exception as e:
        print(f"  Error IPC España: {e}")

    # ── IPC Chile ──────────────────────────────────────────────────
    separador("2. IPC Chile (World Bank)")
    try:
        registros_cl = obtener_ipc_chile()
        existentes   = meses_existentes_ipc(conn, "Chile")
        nuevos = [r for r in registros_cl
                  if (r["anio"], r["mes"]) not in existentes]
        if nuevos:
            pd.DataFrame(nuevos).to_sql(
                "mercado_ipc", engine, if_exists="append", index=False
            )
            print(f"  Guardados {len(nuevos)} meses nuevos de IPC Chile")
            for r in nuevos[-3:]:
                campo = r.get('ipc_variacion_mensual', r.get('ipc_variacion_anual', '?'))
                print(f"    {MESES[r['mes']]} {r['anio']}: {campo}% var. mensual")
        else:
            print("  IPC Chile ya actualizado")
    except Exception as e:
        print(f"  Error IPC Chile: {e}")

    # ── Índice alquiler ────────────────────────────────────────────
    separador("3. Índice alquiler Salamanca y Madrid (INE)")
    try:
        registros_alq = obtener_indice_alquiler()
        nuevos_alq = []
        for r in registros_alq:
            existentes = anios_existentes_alquiler(
                conn, r["zona"], r["tipo_contrato"]
            )
            if r["anio"] not in existentes:
                nuevos_alq.append(r)
        if nuevos_alq:
            pd.DataFrame(nuevos_alq).to_sql(
                "mercado_alquiler", engine, if_exists="append", index=False
            )
            print(f"  Guardados {len(nuevos_alq)} registros nuevos")
            for r in nuevos_alq:
                print(f"    {r['zona']} {r['tipo_contrato']} "
                      f"{r['anio']}: índice {r['indice_base2015']}")
        else:
            print("  Índice alquiler ya actualizado")
    except Exception as e:
        print(f"  Error índice alquiler: {e}")

    # ── Salarios mercado ───────────────────────────────────────────
    separador("4. Salarios mercado Data/BI Madrid")
    try:
        if salarios_desactualizados(conn):
            registros_sal = obtener_salarios()
            pd.DataFrame(registros_sal).to_sql(
                "mercado_salarios", engine, if_exists="replace", index=False
            )
            print(f"  Guardados {len(registros_sal)} perfiles salariales")
            for r in registros_sal:
                print(f"    {r['nivel']:<12} "
                      f"€{r['salario_min']:,}-€{r['salario_max']:,}/año  "
                      f"(€{r['neto_mensual_min']:,}-€{r['neto_mensual_max']:,} neto/mes)")
            print(f"\n  Fuente: {registros_sal[0]['fuente']}")
            print(f"  Próxima revisión recomendada: Abril 2027")
        else:
            print("  Salarios ya actualizados (menos de 365 días)")
            print("  Para forzar actualización: edita SALARIOS_MERCADO en el script")
    except Exception as e:
        print(f"  Error salarios: {e}")

    # ── Resumen tablas ─────────────────────────────────────────────
    separador("Resumen tablas de mercado")
    cur = conn.cursor()
    for tabla in ["mercado_ipc", "mercado_alquiler", "mercado_salarios"]:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tabla}")
            n = cur.fetchone()[0]
            print(f"  {tabla:<22} {n:>4} registros")
        except Exception:
            print(f"  {tabla:<22} no existe aún")

    conn.close()
    print(f"\n  Base de datos: {BASE_DIR / 'finanzas.db'}")
    print("  Ejecuta mensualmente junto con tipo_cambio.py")
    print("="*58)


if __name__ == "__main__":
    main()
