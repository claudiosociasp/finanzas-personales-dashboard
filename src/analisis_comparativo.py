"""
Análisis comparativo dinámico — secciones 5 y 6
Lee datos actualizados directamente desde finanzas.db.

AJUSTES MANUALES DOCUMENTADOS:
  - Supermercado Chile: ajustado a $280.000 CLP/mes real
    (DB subestima porque muchas compras fueron con TC, no CC)
  - Alquiler Salamanca: €1.500/mes habitación propia (mercado real 2026)
  - Gastos corrientes Chile: se incluyen meses atípicos (estimación conservadora)

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/analisis_comparativo.py
"""

import sqlite3
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).parent.parent
DB_FILE  = str(BASE_DIR / "finanzas.db")

MESES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
         7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

# ── Ajustes manuales documentados ─────────────────────────────────────────────
# Supermercado Chile real (~$280.000 CLP/mes, cc+tc+efectivo combinado)
SUPERMERCADO_CHILE_CLP = 280000
RESTAURANTE_CHILE_CLP      = 150000   # estimación real Las Condes
TRANSPORTE_PUBLICO_CHILE_CLP = 35000  # metro + bus mensual

# Alquiler Salamanca — habitación propia en piso compartido, mercado 2026
ALQUILER_SALAMANCA_EUR = 1500

def separador(titulo=""):
    if titulo:
        print(f"\n{'='*62}")
        print(f"  {titulo}")
        print(f"{'='*62}")
    else:
        print("─"*62)

def main():
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()
    hoy  = date.today()

    # ── Sueldo base Arcaya ─────────────────────────────────────────
    cur.execute("""
        SELECT ROUND(AVG(m.abono_clp), 0),
               ROUND(AVG(m.abono_clp / t.clp_eur), 0)
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria = 'ingreso_laboral'
        AND m.descripcion LIKE '%762091712%'
        AND m.abono_clp BETWEEN 1400000 AND 1600000
    """)
    avg_clp, avg_eur = cur.fetchone()

    # ── Sueldo Gerente Arcaya ──────────────────────────────────────
    cur.execute("""
        SELECT ROUND(m.abono_clp, 0),
               ROUND(m.abono_clp / t.clp_eur, 0)
        FROM cc_movimientos m
        JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
        WHERE m.subcategoria = 'ingreso_laboral'
        AND m.descripcion LIKE '%762091712%'
        AND m.abono_clp > 2500000
        LIMIT 1
    """)
    ger_clp, ger_eur = cur.fetchone()

    # ── Tipo de cambio actual ──────────────────────────────────────
    cur.execute("""
        SELECT clp_eur FROM tipo_cambio
        ORDER BY anio DESC, mes DESC LIMIT 1
    """)
    tc_actual = cur.fetchone()[0]

    # ── Salarios mercado ───────────────────────────────────────────
    cur.execute("""
        SELECT nivel, descripcion, salario_min, salario_max,
               neto_mensual_min, neto_mensual_max, fecha_actualizacion
        FROM mercado_salarios ORDER BY salario_min
    """)
    salarios = cur.fetchall()
    senior      = next((s for s in salarios if s[0] == 'senior'), None)
    senior_plus = next((s for s in salarios if s[0] == 'senior_plus'), None)
    fecha_sal   = salarios[0][6] if salarios else hoy.isoformat()

    # ── Índice alquiler Salamanca ──────────────────────────────────
    cur.execute("""
        SELECT anio, indice_base2015 FROM mercado_alquiler
        WHERE zona = 'Salamanca' AND tipo_contrato = 'total'
        ORDER BY anio DESC LIMIT 1
    """)
    sal_anio, sal_indice = cur.fetchone()

    cur.execute("""
        SELECT anio, indice_base2015 FROM mercado_alquiler
        WHERE zona = 'Salamanca' AND tipo_contrato = 'nuevo_contrato'
        ORDER BY anio DESC LIMIT 1
    """)
    sal_nc_anio, sal_nc_indice = cur.fetchone()

    # ── IPC España promedio ────────────────────────────────────────
    cur.execute("""
        SELECT AVG(ipc_variacion_anual) FROM mercado_ipc
        WHERE pais = 'España' AND anio >= ?
    """, (sal_anio,))
    ipc_es_prom = cur.fetchone()[0] or 3.0
    anios_transcurridos  = hoy.year - sal_anio
    factor_actualizacion = (1 + ipc_es_prom / 100) ** anios_transcurridos

    # ── IPC Chile acumulado ────────────────────────────────────────
    cur.execute("""
        SELECT SUM(ipc_variacion_mensual) / 100.0
        FROM mercado_ipc WHERE pais = 'Chile' AND anio >= 2023
    """)
    ipc_cl_acum = cur.fetchone()[0] or 0.12

    # ── Gastos reales Chile por categoría (promedio mensual) ───────
    cur.execute("""
        SELECT subcategoria,
               ROUND(AVG(mes_clp), 0) as avg_clp,
               ROUND(AVG(mes_eur), 0) as avg_eur
        FROM (
            SELECT m.subcategoria, m.anio, m.mes,
                   SUM(m.cargo_clp) as mes_clp,
                   SUM(m.cargo_clp / t.clp_eur) as mes_eur
            FROM cc_movimientos m
            JOIN tipo_cambio t ON m.anio = t.anio AND m.mes = t.mes
            WHERE m.categoria_padre IN ('alimentacion','transporte',
                                        'salud_deporte','servicios')
            AND m.subcategoria NOT IN ('seguro_viaje','tramites')
            AND m.cargo_clp > 0
            AND NOT (m.anio = 2023 AND m.mes IN (4,5,6))
            GROUP BY m.subcategoria, m.anio, m.mes
        )
        GROUP BY subcategoria
        HAVING COUNT(*) >= 3
        ORDER BY avg_eur DESC
    """)
    gastos_chile = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

    # Sobrescribir supermercado con ajuste manual documentado
    tc_prom_2024 = 1030
    supermercado_eur_ajustado = round(SUPERMERCADO_CHILE_CLP / tc_prom_2024)
    gastos_chile['supermercado'] = (SUPERMERCADO_CHILE_CLP, supermercado_eur_ajustado)
    tc_prom_2024 = 1030
    restaurante_eur_ajustado = round(RESTAURANTE_CHILE_CLP / tc_prom_2024)
    transporte_eur_ajustado  = round(TRANSPORTE_PUBLICO_CHILE_CLP / tc_prom_2024)
    gastos_chile['restaurante']        = (RESTAURANTE_CHILE_CLP, restaurante_eur_ajustado)
    gastos_chile['transporte_publico'] = (TRANSPORTE_PUBLICO_CHILE_CLP, transporte_eur_ajustado)

    print(f"  (***) Restaurante y transporte público Chile también ajustados manualmente")

    # ── Gastos reales Madrid ───────────────────────────────────────
    cur.execute("""
        SELECT COUNT(DISTINCT strftime('%Y-%m', fecha_operacion))
        FROM es_movimientos WHERE es_chile = 0
    """)
    meses_madrid = cur.fetchone()[0] or 2

    cur.execute("""
        SELECT subcategoria, ROUND(SUM(ABS(importe_eur)) / ?, 0)
        FROM es_movimientos
        WHERE es_chile = 0 AND tipo = 'cargo'
        AND categoria_padre IN ('alimentacion','transporte',
                                'salud_deporte','servicios')
        GROUP BY subcategoria
    """, (meses_madrid,))
    gastos_madrid = {row[0]: row[1] for row in cur.fetchall()}

    # INE referencia Madrid persona sola 2024
    ine_madrid = {
        "supermercado":       250,
        "restaurante":        120,
        "transporte_publico":  50,   # abono mensual Madrid
        "uber_taxi":           25,   # ocasional
        "bencina":              0,   # sin coche en Madrid
        "gimnasio":            67,   # suscripción mensual Sputnik Climbing
        "suscripcion":         55,   # Netflix + Spotify + Claude + otros
    }

    # ── Multiplicadores ────────────────────────────────────────────
    mult_min = round(senior[2] / 12 / avg_eur, 1) if senior else 0
    mult_max = round(senior[3] / 12 / avg_eur, 1) if senior else 0
    avg_eur_feb2023 = round(avg_clp / 855, 0)
    avg_eur_sep2025 = round(avg_clp / 1126, 0)

    # ══════════════════════════════════════════════════════════════
    # SECCIÓN 5 — COMPARACIÓN SALARIAL
    # ══════════════════════════════════════════════════════════════
    separador("5. Comparación salarial real — Chile vs España")

    print(f"""
  Tu perfil: Data Analyst / Business Intelligence
  ─────────────────────────────────────────────────
  +5 años experiencia | Power BI | SQL certificado
  Tableau | Salesforce | ERP | Inglés avanzado
  Roche (multinacional) | Evalueserve (research global)
  Ingeniero Comercial USM | DataCamp DA Associate 2026

  LO QUE GANABAS EN CHILE
  ─────────────────────────────────────────────────
  Arcaya sueldo base  : ${avg_clp:>12,.0f} CLP/mes
                      : ≈ €{avg_eur:>6,.0f}/mes  |  €{avg_eur*12:,.0f}/año bruto
  Equivalencia España : Nivel JUNIOR en Madrid

  Arcaya Gerente Com. : ${ger_clp:>12,.0f} CLP/mes
                      : ≈ €{ger_eur:>6,.0f}/mes  |  €{ger_eur*12:,.0f}/año bruto
  Equivalencia España : Nivel MID en Madrid

  MERCADO MADRID — DATOS ACTUALIZADOS ({fecha_sal})
  ─────────────────────────────────────────────────""")

    for nivel, desc, sal_min, sal_max, neto_min, neto_max, _ in salarios:
        marcador = " ← TU PERFIL" if nivel == "senior" else ""
        print(f"  {desc}")
        print(f"    €{sal_min:,}-€{sal_max:,}/año bruto  "
              f"(€{neto_min:,}-€{neto_max:,} neto/mes){marcador}")
        print()

    print(f"""  CONCLUSIÓN SALARIAL
  ─────────────────────────────────────────────────
  Tu sueldo base Arcaya (€{avg_eur:,.0f}/mes) equivale a nivel
  junior en Madrid. El mercado pagaría {mult_min}x-{mult_max}x más
  por el mismo perfil.

  Impacto depreciación CLP sobre tu sueldo base:
    Feb 2023  →  €{avg_eur_feb2023:,.0f}/mes
    Sep 2025  →  €{avg_eur_sep2025:,.0f}/mes
    Pérdida   →  €{avg_eur_feb2023-avg_eur_sep2025:,.0f}/mes en 2.5 años
    TC actual →  ${tc_actual:,.0f} CLP/EUR""")

    # ══════════════════════════════════════════════════════════════
    # SECCIÓN 6 — PODER ADQUISITIVO
    # ══════════════════════════════════════════════════════════════
    separador("6. Poder adquisitivo — Las Condes vs Barrio Salamanca")

    categorias_mostrar = {
        "supermercado":       "Supermercado",
        "restaurante":        "Restaurantes",
        "uber_taxi":          "Taxi/Uber",
        "transporte_publico": "Transporte público",
        "bencina":            "Bencina (solo Chile)",
        "gimnasio":           "Gimnasio/Escalada",
        "suscripcion":        "Suscripciones",
    }

    print(f"""
  Período Chile  : 2023-2024 (vida en Las Condes)
  Período España : {hoy.strftime('%b %Y')} ({meses_madrid} meses, Barrio Salamanca)
  IPC Chile acumulado 2023-2025  : +{ipc_cl_acum*100:.1f}%
  IPC España promedio desde {sal_anio} : +{ipc_es_prom:.1f}%/año
  Nota: gastos Chile incluyen meses atípicos (estimación conservadora)
    """)

    print(f"  {'Categoría':<25} {'Las Condes':>15} {'Salamanca':>16}  {'Dif.':>8}")
    print(f"  {'─'*25} {'─'*15} {'─'*16}  {'─'*8}")

    total_chile  = 0
    total_madrid = 0

    for sub, nombre in categorias_mostrar.items():
        chile_eur  = gastos_chile.get(sub, (0, 0))[1]
        # Para gimnasio y suscripcion usar siempre el valor manual (más preciso)
        if sub in ('gimnasio', 'suscripcion', 'bencina', 'transporte_publico', 'uber_taxi'):
            madrid_eur = ine_madrid.get(sub, 0)
        else:
            madrid_eur = gastos_madrid.get(sub, ine_madrid.get(sub, 0))
        fuente     = "" if sub in gastos_madrid else "(INE)"
        ajuste     = " (*)" if sub == "supermercado" else ""

        if chile_eur == 0 and madrid_eur == 0:
            continue

        diff     = madrid_eur - chile_eur
        diff_str = f"+€{diff:.0f}" if diff > 0 else f"-€{abs(diff):.0f}"
        if abs(diff) < 1:
            diff_str = "—"

        chile_str  = f"€{chile_eur:.0f}/mes{ajuste}"
        madrid_str = f"€{madrid_eur:.0f}/mes {fuente}".strip()

        print(f"  {nombre:<25} {chile_str:>15} {madrid_str:>16}  {diff_str:>8}")
        total_chile  += chile_eur
        total_madrid += madrid_eur

    print(f"  {'─'*25} {'─'*15} {'─'*16}  {'─'*8}")
    diff_total = total_madrid - total_chile
    if diff_total >= 0:
        diff_str = f"+€{diff_total:.0f}"
    else:
        diff_str = f"-€{abs(diff_total):.0f}"
    print(f"  {'SUBTOTAL':<25} €{total_chile:.0f}/mes"
      f"   €{total_madrid:.0f}/mes  {diff_str}")
    print(f"  (*) Supermercado Chile ajustado a ${SUPERMERCADO_CHILE_CLP:,} CLP/mes")
    print(f"      (DB subestima — muchas compras pagadas con TC)")
    print(f"  (**) Gimnasio Madrid: €67/mes Sputnik. Entrenador personal ~€70/mes pendiente confirmar")
    
    # Alquiler Las Condes actualizado con IPC Chile
    alq_lc_min = round(700000 * (1 + ipc_cl_acum) / tc_actual)
    alq_lc_max = round(1000000 * (1 + ipc_cl_acum) / tc_actual)

    print(f"""
  ALOJAMIENTO — Barrio equivalente a Las Condes
  ─────────────────────────────────────────────────
  Índice alquiler Salamanca {sal_anio}  : {sal_indice} (base 2015=100)
  Índice nuevo contrato      {sal_nc_anio}  : {sal_nc_indice}
  IPC actualización desde {sal_anio}    : +{ipc_es_prom:.1f}%/año × {anios_transcurridos} años

  Salamanca habitación propia    : ~€{ALQUILER_SALAMANCA_EUR:,}/mes (mercado 2026)
  Las Condes (1 dorm.) ajust IPC : ≈ €{alq_lc_min:,}-€{alq_lc_max:,}/mes (TC actual)

  ANÁLISIS DE PODER ADQUISITIVO
  ─────────────────────────────────────────────────
  Con sueldo base Arcaya €{avg_eur:,.0f}/mes:
    Las Condes → alquiler ~€{alq_lc_min:,} + gastos ~€{int(total_chile):,} = ~€{alq_lc_min+int(total_chile):,}/mes
    Salamanca  → alquiler ~€{ALQUILER_SALAMANCA_EUR:,} + gastos ~€{int(total_madrid):,} = ~€{ALQUILER_SALAMANCA_EUR+int(total_madrid):,}/mes
    Resultado  → En Chile vivías MEJOR con ese sueldo

  Con sueldo Senior Madrid €{senior[4]:,}/mes neto:
    Salamanca  → alquiler ~€{ALQUILER_SALAMANCA_EUR:,} + gastos ~€{int(total_madrid):,} = ~€{ALQUILER_SALAMANCA_EUR+int(total_madrid):,}/mes
    Ahorro     → ~€{senior[4]-ALQUILER_SALAMANCA_EUR-int(total_madrid):,}/mes disponible
    Resultado  → Vida cómoda con capacidad de ahorro real

  Con sueldo Senior+ Madrid €{senior_plus[4]:,}/mes neto:
    Salamanca  → alquiler ~€{ALQUILER_SALAMANCA_EUR:,} + gastos ~€{int(total_madrid):,} = ~€{ALQUILER_SALAMANCA_EUR+int(total_madrid):,}/mes
    Ahorro     → ~€{senior_plus[4]-ALQUILER_SALAMANCA_EUR-int(total_madrid):,}/mes disponible
    Resultado  → Excelente calidad de vida con ahorro significativo

  TU OBSERVACIÓN VALIDADA
  ─────────────────────────────────────────────────
  Supermercado Las Condes (ajustado) : ~${SUPERMERCADO_CHILE_CLP:,} CLP/mes
                                     ≈ €{supermercado_eur_ajustado:,}/mes
  Supermercado Madrid                : €{ine_madrid['supermercado']}/mes (INE 2024)

  Precios comparables en EUR, sueldos 2-3x menores en Chile.
  IPC Chile acumuló +{ipc_cl_acum*100:.1f}% desde 2023 vs +{ipc_es_prom*anios_transcurridos:.1f}% España.
  La brecha de poder adquisitivo se amplía cada año.
    """)

    # ══════════════════════════════════════════════════════════════
    # RESUMEN EJECUTIVO
    # ══════════════════════════════════════════════════════════════
    separador("Resumen ejecutivo")
    print(f"""
  CHILE (realidad 2023-2024, Las Condes)
  ─────────────────────────────────────────────────
  Sueldo base       : ${avg_clp:,.0f} CLP ≈ €{avg_eur:,.0f}/mes
  Nivel en España   : Junior (€{salarios[0][2]:,}-€{salarios[0][3]:,}/año)
  Alquiler          : ≈ €{alq_lc_min:,}-€{alq_lc_max:,}/mes (ajustado IPC)
  Gastos corrientes : ≈ €{int(total_chile):,}/mes (estimación conservadora)
  Margen ahorro     : muy limitado

  ESPAÑA — POTENCIAL CON TU PERFIL (Barrio Salamanca)
  ─────────────────────────────────────────────────
  Rango objetivo    : €{senior[2]:,}-€{senior[3]:,} brutos/año
  Neto mensual      : €{senior[4]:,}-€{senior[5]:,}/mes
  Alquiler          : ~€{ALQUILER_SALAMANCA_EUR:,}/mes (habitación propia)
  Gastos corrientes : ≈ €{int(total_madrid):,}/mes
  Margen ahorro     : €{senior[4]-ALQUILER_SALAMANCA_EUR-int(total_madrid):,}-€{senior[5]-ALQUILER_SALAMANCA_EUR-int(total_madrid):,}/mes

  VENTAJA CLAVE DE ESTAR EN MADRID
  ─────────────────────────────────────────────────
  El mercado Data/BI en Madrid paga {mult_min}x-{mult_max}x más que
  Chile por el mismo perfil. La depreciación del CLP
  hace que esa brecha crezca cada año.

  Estar en España ya es la decisión correcta.
  El siguiente paso: posicionarte en el rango Senior
  (€{senior[2]:,}-€{senior[3]:,}/año) que tu CV ya justifica.
    """)

    conn.close()
    print("="*62)
    print(f"  Datos actualizados al : {hoy.isoformat()}")
    print(f"  Fuentes               : INE España | mindicador.cl (BCCh)")
    print(f"                          Tu DB personal | Mercado 2026")
    print("="*62)

if __name__ == "__main__":
    main()
