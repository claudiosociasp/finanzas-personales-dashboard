# 📊 Finanzas Personales — Dashboard de Análisis Financiero

> Proyecto de portfolio en Python que integra datos bancarios reales de Chile y España para construir un sistema completo de análisis financiero personal con dashboard interactivo.

**Stack:** Python · SQLite · Pandas · Dash · Plotly · SQL · APIs REST

---

## 🎯 Contexto y motivación

Proyecto desarrollado durante mi transición profesional de Santiago de Chile a Madrid (2023–2026). Combina datos reales de tres fuentes bancarias para responder preguntas concretas:

- ¿Cuánto perdí en poder adquisitivo por la depreciación del CLP?
- ¿Cuál es mi tasa de ahorro real incluyendo gastos de tarjeta de crédito?
- ¿Cómo se compara el costo de vida en Las Condes vs Barrio Salamanca?
- ¿Cuánto ahorro liquidando mi deuda en septiembre 2026 vs seguir en cuotas?
- ¿Qué sueldo debería exigir en Madrid según mi perfil senior de BI?

---

## 🏗️ Arquitectura del proyecto

```
finanzas_personales/
├── src/
│   ├── etl_tarjeta.py          # ETL estados de cuenta TC (PDF → SQLite)
│   ├── etl_cuenta.py           # ETL cuenta corriente (Excel → SQLite)
│   ├── etl_global66_santander_españa.py  # ETL Global66 + Santander España
│   ├── categorias.py           # 346 palabras clave → 8 categorías padre
│   ├── recategorizar.py        # Aplicar categorías a todas las tablas
│   ├── tipo_cambio.py          # TC CLP/EUR histórico (BCCh + API)
│   ├── actualizar_mercado.py   # IPC, alquiler, salarios (INE + BCCh + WB)
│   ├── analisis_comparativo.py # Análisis Chile vs España
│   ├── queries_avanzadas.py    # 10 queries SQL con insights financieros
│   ├── dashboard_app.py        # Dashboard interactivo Dash
│   └── generar_demo.py         # Genera DB demo con datos anonimizados
├── datos_macro/                # Archivos BCCh (TC histórico)
├── finanzas_demo.db            # DB demo con datos anonimizados ±15%
├── .env.example                # Variables de entorno (copiar como .env)
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

El dashboard incluye **filtros globales** (año / trimestre / mes) que actualizan todos los gráficos simultáneamente.

### Sección 1 — Mercado cambiario e ingresos
- Evolución tipo de cambio CLP/EUR con promedio y hitos
- Ingresos laborales por empresa con tendencia y ecuación de la recta

### Sección 2 — Evolución de gastos y deuda
- Gasto mensual CC desglosado (corriente vs deuda) con tendencia
- Evolución deuda TC con saldo pendiente y proyección liquidación

### Sección 3 — Distribución de gastos
- Barras horizontales agrupadas por categoría y subcategoría

### Sección 4 — Análisis comparativo Chile vs España
- Poder adquisitivo Las Condes vs Salamanca ajustado por IPC
- Comparación salarial Data/BI con rangos de mercado Madrid 2026

### Sección 5 — Análisis financiero avanzado
- Gastos mensuales CC + TC vs ingresos reales
- Top 10 categorías gasto tarjeta de crédito
- Tasa de ahorro real mensual (CC + TC)
- Top 10 comercios por gasto total
- Proyección liquidación deuda: Escenario A (cuotas) vs B (liquidar sep 2026)

---

## 🔍 Queries SQL avanzadas (`queries_avanzadas.py`)

| Query | Insight |
|-------|---------|
| Q1 | Ingreso real neto mensual promedio por empresa |
| Q3 | Top 10 comercios por gasto total |
| Q5 | % ingresos destinado a deuda (solo CC) |
| Q5b | % ingresos destinado a deuda (CC + TC real) |
| Q6 | Intereses reales vs capital amortizado |
| Q7 | Ahorro por liquidar deuda en sep 2026 vs seguir en cuotas |
| Q8 | Tasa de ahorro real (solo CC) |
| Q8b | Tasa de ahorro real (CC + TC) — revela gasto oculto |
| Q9 | Gasto corriente Las Condes vs Barrio Salamanca |

### Hallazgos clave
- **Depreciación CLP:** pérdida de €420/mes en poder adquisitivo entre feb 2023 y sep 2025
- **Gasto oculto TC:** tasa de ahorro aparente 57.9% (solo CC) → tasa real 3.1% (con TC)
- **Liquidación deuda:** ahorro de €725 en intereses + libera €265/mes desde oct 2026
- **Mercado Madrid:** el mismo perfil senior paga 2.1x–2.6x más que en Chile
- **Costo de vida:** Madrid €525/mes vs Las Condes €1.038/mes en gastos corrientes

---

## 🚀 Instalación y uso

### Requisitos
- Python 3.9+
- pip

### Setup

```bash
git clone https://github.com/tu-usuario/finanzas-personales.git
cd finanzas-personales

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

### Ejecutar análisis

```bash
python src/analisis_comparativo.py  # Comparación Chile vs España
python src/queries_avanzadas.py     # 10 queries con insights
```

---

## 🔒 Privacidad de datos

El repositorio incluye `finanzas_demo.db` con datos **sintéticos y anonimizados**:
- Montos alterados con ruido aleatorio ±15%
- Nombres de empresas reemplazados por `EMPRESA_A` / `EMPRESA_B`
- RUTs reemplazados por `RUT_ANONIMO`
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
| Dash 4.1 + Plotly 6.7 | Dashboard interactivo |
| APIs REST | IPC, TC, alquiler, salarios |

---

## 👤 Autor

**Claudio Socias Paradiz**
Data Analyst / Business Intelligence — +5 años experiencia
Santiago de Chile → Madrid, España

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Claudio_Socias-blue)](https://linkedin.com/in/tu-perfil)

---

*Proyecto desarrollado como parte de mi portfolio de Data Analytics. Los datos financieros son propios y han sido anonimizados para su publicación.*
