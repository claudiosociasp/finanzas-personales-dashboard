# 📊 Finanzas Personales — Dashboard de Análisis Financiero

> Proyecto de portfolio completo en Python que integra datos bancarios reales de Chile y España para construir un sistema de análisis financiero personal con ETL automatizado, base de datos SQLite, queries SQL avanzadas y dashboard interactivo publicado en la nube.

**Stack:** Python · SQLite · Pandas · Dash · Plotly · SQL · APIs REST  
**Código:** 5.627 líneas · 17 scripts · 1 dashboard interactivo · 10 queries SQL avanzadas  
**Demo:** [finanzas-personales-dashboard.onrender.com](https://finanzas-personales-dashboard.onrender.com)  
**Repo:** [github.com/claudiosociasp/finanzas-personales-dashboard](https://github.com/claudiosociasp/finanzas-personales-dashboard)

---

## 🎯 Contexto y motivación

Proyecto desarrollado durante mi transición profesional de Santiago de Chile a Madrid (2023–2026). Combina datos reales de tres fuentes bancarias para responder preguntas concretas:

- ¿Cuánto perdí en poder adquisitivo por la depreciación del CLP frente al EUR?
- ¿Cuál es mi tasa de ahorro real incluyendo gastos de tarjeta de crédito?
- ¿Cómo se compara el costo de vida en Las Condes vs Barrio Salamanca?
- ¿Cuánto ahorro liquidando mi deuda en septiembre 2026 vs seguir en cuotas?
- ¿Qué sueldo debería exigir en Madrid según mi perfil senior de BI?

---

## 🏗️ Arquitectura del proyecto

```
finanzas_personales/
├── src/
│   ├── etl_tarjeta.py                    # ETL estados de cuenta TC (PDF → SQLite)
│   ├── etl_cuenta.py                     # ETL cuenta corriente (Excel → SQLite)
│   ├── etl_global66_santander_españa.py  # ETL Global66 + Santander España
│   ├── categorias.py                     # 346 palabras clave → 8 categorías padre
│   ├── recategorizar.py                  # Aplicar categorías a todas las tablas
│   ├── tipo_cambio.py                    # TC CLP/EUR histórico (BCCh + API)
│   ├── actualizar_mercado.py             # IPC, alquiler, salarios (INE + BCCh + WB)
│   ├── analisis_comparativo.py           # Análisis Chile vs España
│   ├── queries_avanzadas.py              # 10 queries SQL con insights financieros
│   ├── dashboard_app.py                  # Dashboard interactivo Dash (1.034 líneas)
│   └── generar_demo.py                   # Genera DB demo con datos anonimizados
├── datos_macro/                          # Archivos BCCh (TC histórico)
├── finanzas_demo.db                      # DB demo con datos anonimizados ±18%
├── Procfile                              # Configuración deploy Render
├── .env.example                          # Variables de entorno (copiar como .env)
└── requirements.txt
```

---

## 🗄️ Modelo de datos

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  cc_movimientos │     │   tc_compras     │     │  es_movimientos │
│  2.251 filas    │     │   884 filas      │     │  24 filas       │
│  Santander CL   │     │   TC Santander   │     │  Santander ES   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                        │
         └───────────────────────┴────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      tipo_cambio        │
                    │   CLP/EUR 2023-2026     │
                    │      40 registros       │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
    ┌─────────▼──────┐  ┌───────▼────────┐  ┌──────▼──────────┐
    │  mercado_ipc   │  │mercado_alquiler│  │mercado_salarios │
    │  IPC CL + ES   │  │  INE España    │  │  Data/BI Madrid │
    └────────────────┘  └────────────────┘  └─────────────────┘
```

**Total registros:** 4.399 filas · 10 tablas · 346 reglas de categorización · 0 sin clasificar

---

## 📡 Fuentes de datos e integraciones

| Fuente | Tipo | Datos | Frecuencia |
|--------|------|-------|------------|
| Santander Chile (CC) | Excel | Movimientos cuenta corriente | Manual mensual |
| Santander Chile (TC) | PDF | Estados de cuenta tarjeta | Manual mensual |
| Santander España | XLS | Movimientos cuenta española | Manual mensual |
| Global66 | PDF | Transferencias internacionales | Manual mensual |
| mindicador.cl → BCCh | API REST | IPC Chile mensual | Automático |
| INE España | API REST | IPC España + índice alquiler | Automático |
| Banco Central Chile | XLSX | TC CLP/USD, EUR/USD histórico | Manual anual |
| exchangerate-api.com | API REST | TC actual CLP/EUR | Automático |
| World Bank | API REST | IPC Chile anual (respaldo) | Automático |

---

## 📊 Dashboard interactivo

**URL pública:** [finanzas-personales-dashboard.onrender.com](https://finanzas-personales-dashboard.onrender.com)

El dashboard incluye **filtros globales** (año / trimestre / mes) que actualizan todos los gráficos simultáneamente y **6 KPIs dinámicos**: ingresos laborales, gasto total, costo deuda, TC promedio, saldo deuda TC y balance estimado.

### Sección 1 — Mercado cambiario e ingresos laborales
- Evolución tipo de cambio CLP/EUR con promedio histórico
- Ingresos laborales por empresa (PwC / Clínica Arcaya / Por Cuenta Propia) con tendencia

### Sección 2 — Evolución de gastos y balance
- Gasto mensual desglosado (corriente vs deuda TC) con tendencia
- Balance mensual (todos los ingresos − todos los gastos)

### Sección 3 — Distribución de gastos
- Barras horizontales agrupadas por categoría y subcategoría (8 categorías padre, 30+ subcategorías)

### Sección 4 — Análisis comparativo Chile vs España
- Poder adquisitivo Las Condes vs Barrio Salamanca ajustado por IPC
- Comparación salarial Data/BI con rangos de mercado Madrid 2026

### Sección 5 — Análisis financiero avanzado
- Gastos mensuales CC + TC vs ingresos reales
- Top 10 categorías gasto tarjeta de crédito (histórico)
- Tasa de ahorro real mensual (CC + TC)
- Top 10 comercios por gasto total
- Proyección liquidación deuda: Escenario A (cuotas) vs B (liquidar sep 2026)

---

## 🔍 Queries SQL avanzadas

| Query | Insight clave |
|-------|---------------|
| Q1 | Ingreso real neto mensual promedio por empresa |
| Q3 | Top 10 comercios por gasto total |
| Q5 | % ingresos destinado a deuda (solo CC) — promedio 12.8% |
| Q5b | % ingresos destinado a deuda (CC + TC) — promedio 67.6% |
| Q6 | Intereses reales vs capital amortizado — costo financiero €743 |
| Q7 | Ahorro por liquidar deuda sep 2026 — €725 en intereses |
| Q8 | Tasa de ahorro aparente (solo CC) — 57.9% |
| Q8b | Tasa de ahorro real (CC + TC) — 3.1% |
| Q9 | Gasto corriente Las Condes €1.038/mes vs Salamanca €525/mes |

### Hallazgos clave
- **Depreciación CLP:** pérdida de €420/mes en poder adquisitivo feb 2023 → sep 2025
- **Gasto oculto TC:** tasa de ahorro aparente 57.9% → tasa real 3.1% al incluir TC
- **Liquidación deuda:** ahorro de €725 + libera €265/mes desde oct 2026
- **Mercado Madrid:** mismo perfil senior paga 2.1x–2.6x más que en Chile
- **Costo de vida:** Madrid €525/mes vs Las Condes €1.038/mes en gastos corrientes

---

## 👤 Perfil profesional vs mercado Madrid

El proyecto incluye un análisis comparativo del mercado salarial Data/BI en Madrid basado en datos de Glassdoor y LinkedIn 2026:

- **Perfil**: Data Analyst / BI Senior (+5 años experiencia)
- **Stack**: Power BI, SQL, Tableau, Salesforce, Python (en progreso)
- **Empresas**: PricewaterhouseCoopers, Clínica Lo Arcaya
- **Rango estimado Madrid**: €38.000 — €46.000/año bruto
- **Referencia Chile**: €40.306/año bruto (último cargo)

El gráfico "Comparación Salarial: Chile vs Madrid" muestra que el mismo perfil senior en Madrid equivale a 2.1x–2.6x el salario equivalente en Chile.

---

## 🚀 Instalación y uso

### Requisitos
- Python 3.9+
- pip

### Setup

```bash
git clone https://github.com/claudiosociasp/finanzas-personales-dashboard.git
cd finanzas-personales-dashboard

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
```

### Ejecutar con datos demo

```bash
# El repo incluye finanzas_demo.db con datos anonimizados
python src/dashboard_app.py
# Abre http://127.0.0.1:8050
```

### Actualizar datos de mercado

```bash
python src/tipo_cambio.py          # TC CLP/EUR
python src/actualizar_mercado.py   # IPC, alquiler, salarios
```

### Ejecutar análisis SQL

```bash
python src/queries_avanzadas.py    # 10 queries con insights
python src/analisis_comparativo.py # Comparación Chile vs España
```

### Flujo mensual de actualización

```bash
python src/tipo_cambio.py
python src/actualizar_mercado.py
python src/etl_global66_santander_españa.py  # nuevos extractos
python src/recategorizar.py
```

---

## 🔒 Privacidad de datos

El repositorio incluye `finanzas_demo.db` con datos **sintéticos y anonimizados**:
- Montos alterados con ruido aleatorio ±18%
- Nombres de empresas mantenidos (PwC, Clínica Arcaya — no son datos sensibles)
- RUTs reemplazados por `RUT_ANONIMO`
- Ingresos ficticios sep 2024 → abr 2026 con variabilidad ±23%
- Gastos ficticios sep 2024 → feb 2026 con nombres de comercios chilenos reales
- Datos públicos (tipo de cambio, IPC, índices) copiados tal cual

Los datos financieros reales, PDFs de estados de cuenta y archivos Excel están en `.gitignore`.

---

## 🛠️ Stack tecnológico

| Tecnología | Uso |
|-----------|-----|
| Python 3.9 | Lenguaje principal |
| SQLite + SQLAlchemy | Base de datos local |
| Pandas | ETL y transformación de datos |
| pdfplumber | Extracción de PDFs bancarios |
| Dash 4.x + Plotly 6.x | Dashboard interactivo |
| Gunicorn | Servidor WSGI para producción |
| Render | Deploy en la nube (plan gratuito) |
| APIs REST | IPC, TC, alquiler, salarios |

---

## 📈 Métricas del proyecto

| Métrica | Valor |
|---------|-------|
| Líneas de código Python | 5.627 |
| Scripts desarrollados | 17 |
| Registros procesados | 4.399 |
| Palabras clave de categorización | 346 |
| Registros sin clasificar | 0 |
| Fuentes de datos integradas | 9 |
| Queries SQL avanzadas | 10 |
| Gráficos interactivos | 13 |
| Meses de datos históricos | 38 |

---

## 👨‍💻 Autor

**Claudio Socias Paradiz**  
Data Analyst / Business Intelligence — +5 años experiencia  
Santiago de Chile → Madrid, España

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Claudio_Socias-blue)](https://www.linkedin.com/in/claudio-socías)
[![GitHub](https://img.shields.io/badge/GitHub-claudiosociasp-black)](https://github.com/claudiosociasp)

---

*Proyecto desarrollado como parte de mi portfolio de Data Analytics. Los datos financieros son propios y han sido anonimizados para su publicación.*
