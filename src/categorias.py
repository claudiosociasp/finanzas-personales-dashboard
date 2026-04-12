"""
Gestión de categorías unificadas para todas las fuentes de datos.

IMPORTANTE sobre Chile:
    - "SPA" en Chile significa Sociedad por Acciones (tipo de empresa)
    - NUNCA usar "SPA" como indicador de bienestar/masajes
    - Categorizar SIEMPRE por el nombre completo del comercio

Para agregar nuevas palabras clave:
    1. Edita la lista CATEGORIAS más abajo
    2. Ejecuta: python src/categorias.py
    3. Luego ejecuta: python src/recategorizar.py

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/categorias.py
"""

from pathlib import Path
from sqlalchemy import create_engine
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
DB_PATH  = f"sqlite:///{BASE_DIR / 'finanzas.db'}"

CATEGORIAS = [

    # ── ALIMENTACIÓN ──────────────────────────────────────────────────────────
    ("alimentacion", "supermercado", "UNIMARC",              "chile"),
    ("alimentacion", "supermercado", "JUMBO",                "chile"),
    ("alimentacion", "supermercado", "LIDER",                "chile"),
    ("alimentacion", "supermercado", "TOTTUS",               "chile"),
    ("alimentacion", "supermercado", "STA ISABEL",           "chile"),
    ("alimentacion", "supermercado", "SANTA ISABEL",         "chile"),
    ("alimentacion", "supermercado", "STEFIMA",              "chile"),
    ("alimentacion", "supermercado", "EXPRESS VALPO",        "chile"),
    ("alimentacion", "supermercado", "EXPRESS PUCON",        "chile"),
    ("alimentacion", "supermercado", "GET IT",               "chile"),
    ("alimentacion", "supermercado", "SPACIO 1",             "chile"),
    ("alimentacion", "supermercado", "OKM SUBCENTRO",        "chile"),
    ("alimentacion", "supermercado", "SUPER TODO",           "chile"),
    ("alimentacion", "supermercado", "Super Todo",           "españa"),
    ("alimentacion", "supermercado", "MERCADONA",            "españa"),
    ("alimentacion", "supermercado", "CARREFOUR",            "españa"),
    ("alimentacion", "supermercado", "LIDL",                 "españa"),
    ("alimentacion", "supermercado", "ALDI",                 "españa"),
    ("alimentacion", "supermercado", "DIA ",                 "españa"),
    ("alimentacion", "supermercado",  "SPID SAN DAMIAN",      "chile"),
    ("alimentacion", "supermercado",  "EXPRESS LATADIA",      "chile"),
    ("alimentacion", "supermercado", "EXPRESS ISABEL LA",     "chile"),
    ("alimentacion", "supermercado", "SUPERMERCADO COLISEO", "chile"),
    ("alimentacion", "supermercado", "OPEN KENNEDY",          "chile"),
    ("alimentacion", "supermercado", "MINIMARKET LUKAS",     "chile"),
    ("alimentacion", "supermercado", "OKM COLON",            "chile"),
    ("alimentacion", "supermercado", "OKM QUINCHAMALI",      "chile"),
    ("alimentacion", "supermercado", "LO SALDES APOQUINDO",  "chile"),
    ("alimentacion", "supermercado", "VALLE NEWS",           "chile"),
    ("alimentacion", "supermercado", "SPID LAS CONDES",     "chile"),


    # Restaurantes — NUNCA categorizar por "SPA"
    ("alimentacion", "restaurante",  "BEER GARDEN",          "chile"),
    ("alimentacion", "restaurante",  "MIGUELAYO",            "chile"),
    ("alimentacion", "restaurante",  "LA BIRRA",             "chile"),
    ("alimentacion", "restaurante",  "NOVA SPA",             "chile"),
    ("alimentacion", "restaurante",  "CURACARIBS",           "chile"),
    ("alimentacion", "restaurante",  "NICOLAS CAFE",         "chile"),
    ("alimentacion", "restaurante",  "SUMUP * NICOLAS",      "chile"),
    ("alimentacion", "restaurante",  "KFC",                  "todas"),
    ("alimentacion", "restaurante",  "CARLS JR",             "chile"),
    ("alimentacion", "restaurante",  "FREDDO",               "chile"),
    ("alimentacion", "restaurante",  "STARBUCKS",            "todas"),
    ("alimentacion", "restaurante",  "JARDIN DE HAMBUR",     "chile"),
    ("alimentacion", "restaurante",  "EMPANADAS MATIAS",     "chile"),
    ("alimentacion", "restaurante",  "CAFE ADELE",           "chile"),
    ("alimentacion", "restaurante",  "CHINESE MARK",         "chile"),
    ("alimentacion", "restaurante",  "MERPAGO*LARROSBURGER", "chile"),
    ("alimentacion", "restaurante",  "MERPAGO*SAN CAMILO",   "chile"),
    ("alimentacion", "restaurante",  "LOS TRONCOS",          "chile"),
    ("alimentacion", "restaurante",  "Los Troncos",          "españa"),
    ("alimentacion", "restaurante",  "EXPRESS PD",           "chile"),
    ("alimentacion", "restaurante",  "MERCADOPAGO*RICANDO",  "chile"),
    ("alimentacion", "restaurante",  "ULTIMA LLAMADA",       "chile"),
    ("alimentacion", "restaurante",  "Ultima Llamada",       "españa"),
    ("alimentacion", "restaurante",  "SUMUP * TWIST",        "chile"),
    ("alimentacion", "restaurante",  "PANADERO",             "españa"),
    ("alimentacion", "restaurante",  "MIALCAMPO",            "españa"),
    ("alimentacion", "restaurante",  "CAFECAMPESINO",        "españa"),
    ("alimentacion", "restaurante",  "PAMP",                 "españa"),
    ("alimentacion", "restaurante",  "EMPANDAS PAUL",        "españa"),
    ("alimentacion", "restaurante",  "BARBERIA",             "españa"),
    ("alimentacion", "restaurante",   "ESPACIOS GASTRONOMICOS","chile"),
    ("alimentacion", "restaurante",   "LA VIRGEN",            "chile"),
    ("alimentacion", "restaurante",   "TOMA CAFE",            "españa"),
    ("alimentacion", "restaurante",   "TAMANGO",              "chile"),
    ("alimentacion", "restaurante",   "NEW YORK DELI",        "chile"),
    ("alimentacion", "restaurante",   "SAKURA EXPRESS",       "chile"),
    ("alimentacion", "restaurante",   "OH BOK BUNSIK",        "chile"),
    ("alimentacion", "restaurante",   "EL MONTANES",          "chile"),
    ("alimentacion", "restaurante",   "ALIGOT",               "chile"),
    ("alimentacion", "restaurante",   "DONDOH",               "chile"),
    ("alimentacion", "restaurante",   "RAMEN KINTARO",        "chile"),
    ("alimentacion", "restaurante",   "MIT BURGER",           "chile"),
    ("alimentacion", "restaurante",   "NIU SUSHI",            "chile"),
    ("alimentacion", "restaurante",   "BEASTY BUTCHERS",      "chile"),
    ("alimentacion", "restaurante", "MC DONALDS",         "chile"),
    ("alimentacion", "restaurante", "MERCAT",              "chile"),
    ("alimentacion", "restaurante", "TIP Y TAP",           "chile"),
    ("alimentacion", "restaurante", "ARCA",                "chile"),
    ("alimentacion", "restaurante", "LA FUENTE CARRERA",   "chile"),
    ("alimentacion", "restaurante", "SAKURA",              "chile"),
    ("alimentacion", "restaurante", "CASONA DE GALES",     "chile"),
    ("alimentacion", "restaurante", "BRUNAPOLI",           "chile"),
    ("alimentacion", "restaurante", "CAFETERIA LAIK",      "chile"),
    ("alimentacion", "restaurante", "NUEVOS AMIGOS",       "chile"),
    ("alimentacion", "restaurante", "DAMOA",               "chile"),
    ("alimentacion", "restaurante", "ESTO ES REAL",        "chile"),
    ("alimentacion", "restaurante", "ROOF",                  "chile"),
    ("alimentacion", "restaurante", "GRUPO GASTRONOMICO",    "chile"),
    ("alimentacion", "restaurante", "BOULANGERIE PANAME",    "chile"),
    ("alimentacion", "restaurante", "LE BIRRA",              "chile"),
    ("alimentacion", "restaurante", "EL ESPANOL",            "chile"),
    ("alimentacion", "restaurante", "ALAMBIQUE Y CREPERIE",  "chile"),
    ("alimentacion", "restaurante", "UPA]",                  "chile"),
    ("alimentacion", "restaurante", "UPITA]",                "chile"),
    ("alimentacion", "restaurante", "MERMOZ",                "chile"),
    ("alimentacion", "restaurante", "PEDRO DE VALDIVIA",     "chile"),
    ("alimentacion", "restaurante", "SINATRAS COFFEE",       "chile"),
    ("alimentacion", "restaurante", "ARAMCO LA MACARENA",    "chile"),
    ("alimentacion", "restaurante", "KRISPY KREME",          "chile"),
    ("alimentacion", "restaurante", "CASTANO",               "chile"),
    ("alimentacion", "restaurante", "LAIK",                  "chile"),
    ("alimentacion", "restaurante", "MARTIN DE ZAMORA",      "chile"),
    ("alimentacion", "restaurante", "UPA! F793",             "chile"),
    ("alimentacion", "restaurante", "NORUEGA",               "chile"),

    ("alimentacion", "delivery",     "PAYU *UBER EATS",      "chile"),
    ("alimentacion", "delivery",     "UBER EATS",            "todas"),
    ("alimentacion", "delivery",     "JUSTO",                "chile"),



    ("alimentacion", "licoreria",    "LICORERIAS",           "chile"),
    ("alimentacion", "licoreria",    "CHILEDRINK",           "chile"),
    ("alimentacion", "licoreria",    "OXXO",                 "chile"),
    ("alimentacion", "licoreria",    "MP *LIQUIDOS OFF",     "chile"),
    ("alimentacion", "licoreria",    "TABAQUERIA",           "todas"),

    # ── TRANSPORTE ────────────────────────────────────────────────────────────
    ("transporte", "bencina",          "SHELL",              "chile"),
    ("transporte", "bencina",          "COPEC",              "chile"),
    ("transporte", "bencina",          "Copec Asistido",     "españa"),
    ("transporte", "bencina",          "PETROBRAS",          "chile"),
    ("transporte", "bencina",          "PRONTO",             "chile"),
    ("transporte", "bencina",          "ESMAX",              "chile"),
    ("transporte", "bencina",          "QUILPUE LOS CARRERA","chile"),

    ("transporte", "uber_taxi",        "UBER",               "todas"),
    ("transporte", "uber_taxi",        "CABIFY",             "todas"),
    ("transporte", "uber_taxi",        "TRANSFER T Y T",     "chile"),
    ("transporte", "uber_taxi",        "Transfer T Y T",     "españa"),
    ("transporte", "uber_taxi",     "Compra Internacional UBER", "chile"),

    ("transporte", "car_sharing", "AWTO CLICK", "chile"),

    ("transporte", "transporte_publico","METRO",             "todas"),
    ("transporte", "transporte_publico","BIP",               "chile"),
    ("transporte", "transporte_publico","RENFE",             "españa"),
    ("transporte", "transporte_publico","TICKETPLUS",        "chile"),
    ("transporte", "transporte_publico", "MOVIRED",           "chile"),

    ("transporte", "estacionamiento", "REPUBLIC PARKING",    "chile"),
    ("transporte", "estacionamiento", "CENTRAL PARKING",     "chile"),
    ("transporte", "estacionamiento", "SAN SERGIO ESTAC",    "chile"),
    ("transporte", "estacionamiento", "MT AUT INES",         "chile"),
    ("transporte", "estacionamiento", "PARKING",             "todas"),
    ("transporte", "estacionamiento", "SABA ARAUCO",         "chile"),
    ("transporte", "estacionamiento", "RPS MEGACENTER",      "chile"),

    ("transporte", "avion",           "LATAM",               "todas"),
    ("transporte", "avion",           "AEREAS",              "todas"),
    ("transporte", "avion",           "VUELING",             "españa"),
    ("transporte", "avion",           "IBERIA",              "españa"),
    ("transporte", "avion",           "RYANAIR",             "españa"),
    ("transporte", "avion",           "DUTY FREE SALIDAS",   "chile"),
    ("transporte", "avion",           "TRAVEL MARKET SCL",             "chile"),

    ("transporte", "tren",            "AVE",                 "españa"),
    ("transporte", "tren",            "RedGloba*EFE",        "chile"),

    ("transporte", "bus",             "TUR-BUS",             "chile"),
    ("transporte", "bus",             "TERMINAL ALAMEDA",    "chile"),
    ("transporte", "bus",             "TURBUS WEB",          "chile"),

    ("transporte", "peaje",           "AUTOPISTA",           "chile"),
    ("transporte", "peaje",           "PEAJE",               "chile"),

    ("transporte", "revision_tecnica","PRT LOS TRAPENSES",   "chile"),
    ("transporte", "revision_tecnica","PRT COSTANERA",       "chile"),
    ("transporte", "revision_tecnica","PRT LAS SALINAS",     "chile"),
    ("transporte", "revision_tecnica","PRT ",                "chile"),

    # ── ALOJAMIENTO ───────────────────────────────────────────────────────────
    ("alojamiento", "arriendo",       "ARRIENDO",            "todas"),
    ("alojamiento", "arriendo",       "ALQUILER",            "todas"),
    ("alojamiento", "hotel",          "HOTEL",               "todas"),
    ("alojamiento", "hotel",          "MARRIOTT",            "todas"),
    ("alojamiento", "hotel",          "HILTON",              "todas"),
    ("alojamiento", "hotel",          "SPOT SUITES",         "chile"),
    ("alojamiento", "hostal",         "HOSTAL",              "todas"),
    ("alojamiento", "hostal",         "HOSTEL",              "todas"),
    ("alojamiento", "airbnb",         "AIRBNB",              "todas"),
    ("alojamiento", "airbnb",         "AIRBNB",              "chile"),
    ("alojamiento",  "hostal",        "HOSTEL DEL VALLE",    "chile"),

    # ── SALUD Y DEPORTE ───────────────────────────────────────────────────────
    ("salud_deporte", "seguro_salud", "COLMENA",             "chile"),
    ("salud_deporte", "seguro_salud", "METLIFE",             "chile"),
    ("salud_deporte", "seguro_salud", "ISAPRE",              "chile"),
    ("salud_deporte", "seguro_salud", "SANTANDER SEG",       "chile"),
    ("salud_deporte", "seguro_salud", "0762966190",          "chile"),   # reembolso Colmena

    ("salud_deporte", "medico",       "CLINICA",             "todas"),
    ("salud_deporte", "medico",       "HOSPITAL",            "todas"),
    ("salud_deporte", "medico",       "MEDIC",               "todas"),
    ("salud_deporte", "medico",       "REDSALUD",            "chile"),
    ("salud_deporte", "medico",       "INDISA",              "chile"),
    ("salud_deporte", "medico",       "DENTIQUE",            "chile"),
    ("salud_deporte", "medico",       "ARCAYA SAN DAMIAN",   "chile"),
    ("salud_deporte", "medico",       "BIONET",              "chile"),
    ("salud_deporte", "medico",       "ODONTOLOGICA",        "chile"),

    ("salud_deporte", "farmacia",     "FARMACIA",            "todas"),
    ("salud_deporte", "farmacia",     "CRUZ VERDE",          "chile"),
    ("salud_deporte", "farmacia",     "SALCOBRAND",          "chile"),
    ("salud_deporte", "farmacia",     "SB 634",              "chile"),
    ("salud_deporte", "farmacia",     "AHUM",                "chile"),
    ("salud_deporte", "farmacia",     "SB 609",              "chile"),


    # Gimnasios — siempre por nombre completo, nunca por "SPA"
    ("salud_deporte", "gimnasio",     "MERCADOPAGO*RAGNI",   "chile"),
    ("salud_deporte", "gimnasio",     "MERPAGO*RAGNI",       "chile"),
    ("salud_deporte", "gimnasio",     "COCOSHOUSE",          "chile"),
    ("salud_deporte", "gimnasio",     "BOULDER FACTORY",     "chile"),
    ("salud_deporte", "gimnasio",     "ESCUELA CHILE CLIMBERS","chile"),
    ("salud_deporte", "gimnasio",     "GYM",                 "todas"),
    ("salud_deporte", "gimnasio",     "GIMNASIO",            "todas"),
    ("salud_deporte", "gimnasio",     "FITNESS",             "todas"),
    ("salud_deporte", "gimnasio",     "MCFIT",               "españa"),
    ("salud_deporte", "gimnasio",     "BASIC-FIT",           "españa"),
    ("salud_deporte", "gimnasio",     "GIMNASIO EL MURO",     "chile"),
    ("salud_deporte", "gimnasio",     "ESCUELA DE ESCALADA",  "chile"),
    ("salud_deporte", "gimnasio",     "ESCH9115",             "chile"),
    ("salud_deporte", "gimnasio",     "SPUTNIK CLIM",        "españa"),
    ("salud_deporte", "gimnasio",     "ESCUELA CHILECLIMBERS",   "chile"),
    
    ("salud_deporte", "kinesiologia", "KINUP",                "chile"),

    ("salud_deporte", "cuidado_personal","MADMEN",             "españa"),
    ("salud_deporte", "cuidado_personal", "OLD BARBER",         "chile"),
    ("salud_deporte", "cuidado_personal", "BARBERS CORNER",  "chile"),

    # ── FINANZAS ──────────────────────────────────────────────────────────────
    ("finanzas", "amort_deuda_tc",   "TRASP A CUOTAS",      "chile"),
    ("finanzas", "pago_minimo_tc",   "Pago Autom Tarj",     "chile"),
    

    ("finanzas", "amort_deuda_tc",   "LCA N°",              "chile"),
    ("finanzas", "amort_deuda_tc",   "Amortización",        "chile"),
    ("finanzas", "amort_deuda_tc",   "Amortizacion",        "chile"),    
    
    ("finanzas", "intereses",        "Intereses Línea de Crédito", "chile"),
    ("finanzas", "intereses",        "Intereses Línea",      "chile"),
    ("finanzas", "intereses",        "INTERESES",            "todas"),
    ("finanzas", "intereses",        "INTERÉS",              "todas"),
    

    ("finanzas", "impuestos",        "IMPUESTOS",            "todas"),
    ("finanzas", "impuestos",        "IMPUESTO",             "todas"),
    ("finanzas", "impuestos",        "TIMBRE",               "chile"),
    ("finanzas", "impuestos",        "IVA",                  "chile"),
    ("finanzas", "impuestos",        "PAGO EN LINEA T.G.R.", "chile"),

    ("finanzas", "comision_banco",   "TRASPASO A DEUDA",     "chile"),
    ("finanzas", "comision_banco",   "CAV SUSCRIPCION",      "chile"),
    ("finanzas", "comision_banco",   "SANTANDER SEG FRAUD",  "chile"),
    ("finanzas", "comision_banco",   "COMISION",             "todas"),
    ("finanzas", "comision_banco",   "COMISIÓN",             "todas"),
    ("finanzas", "comision_banco",   "MANTENCIÓN",           "chile"),
    ("finanzas", "comision_banco",   "MANTENCION",           "chile"),

    ("finanzas", "costo_cambio",     "Costo tipo de cambio", "global66"),
    ("finanzas", "costo_cambio",     "Comisión envío",       "global66"),
    ("finanzas", "costo_cambio",     "Egreso por Compra de Divisas","chile"),
    ("finanzas", "costo_cambio",     "Compra  Moneda Extranjera",   "chile"),
    ("finanzas", "costo_cambio",     "Compra Moneda Extranjera",    "chile"),

    ("finanzas", "retiro_efectivo",  "Giro en Efectivo",     "chile"),
    ("finanzas", "retiro_efectivo",  "Giro en Cajero",       "chile"),

    # ── SERVICIOS ─────────────────────────────────────────────────────────────
    ("servicios", "suscripcion",     "SPOTIFY",              "todas"),
    ("servicios", "suscripcion",     "NETFLIX",              "todas"),
    ("servicios", "suscripcion",     "AMAZON",               "todas"),
    ("servicios", "suscripcion",     "DISNEY",               "todas"),
    ("servicios", "suscripcion",     "APPLE",                "todas"),
    ("servicios", "suscripcion",     "MICROSOFT",            "todas"),
    ("servicios", "suscripcion",     "CLAUDE",               "españa"),

    ("servicios", "telefonia",       "ENTEL",                "chile"),
    ("servicios", "telefonia",       "MOVISTAR",             "todas"),
    ("servicios", "telefonia",       "VTR",                  "chile"),
    ("servicios", "telefonia",       "CLARO",                "chile"),
    ("servicios", "telefonia",       "TELEFONICA PROVIDENCIA",     "chile"),

    ("servicios", "plataforma_pago", "MERCADOPAGO",          "todas"),
    ("servicios", "plataforma_pago", "NP PAYU",              "chile"),
    ("servicios", "plataforma_pago", "PAYU",                 "chile"),
    ("servicios", "plataforma_pago", "FINTOC",               "chile"),
    ("servicios", "plataforma_pago", "WEBPAY",               "chile"),
    ("servicios", "plataforma_pago", "SUMUP",                "españa"),
    ("servicios", "plataforma_pago", "MERPAGO",              "todas"),
    ("servicios", "plataforma_pago", "Pago Movil",           "españa"),
    ("servicios", "plataforma_pago", "VENTIPAY",             "chile"),
    ("servicios", "plataforma_pago", "PASSLINE",             "chile"),
    ("servicios", "plataforma_pago", "VENDOMATICA",          "chile"),
    ("servicios", "plataforma_pago", "E SIGN",               "chile"),

    ("servicios", "tramites",        "MUNICIPALIDAD",        "chile"),
    ("servicios", "tramites",        "AUTOFACT",             "chile"),

    ("servicios", "otros_servicios", "DL*AGENDAPRO",         "chile"),
    ("servicios", "otros_servicios", "COM Y SERVICIOS",      "chile"),
    ("servicios", "otros_servicios", "SMARTSOMSPA",          "españa"),


    ("servicios", "seguro_viaje",  "ASISTENCIA DE VIAJE",    "chile"),

    ("servicios", "tramites",      "MUNIC.DE VILLA",         "chile"),

    # ── TRANSFERENCIAS ────────────────────────────────────────────────────────
    ("transferencias", "enviada",    "Envío a cuenta bancaria","global66"),
    ("transferencias", "enviada",    "Envío a",              "global66"),
    ("transferencias", "enviada",    "Transf a",             "chile"),
    ("transferencias", "enviada",    "Transf.",              "chile"),
    ("transferencias", "enviada",    "Giro Internacional",   "chile"),
    ("transferencias", "enviada",    "TRANSFERENCIA INMEDIATA","españa"),
    ("transferencias", "enviada",    "BIZUM",                "españa"),
    ("transferencias", "enviada",    "Calden Garden",        "españa"),   # transferencia a Global66

    ("transferencias", "recibida",   "Recibido de",          "global66"),
    ("transferencias", "recibida",   "Traspaso Internet",    "chile"),
    ("transferencias", "recibida",   "Traspaso con la Cuenta","chile"),
    ("transferencias", "recibida",   "Traspaso mismo Titular","chile"),
    ("transferencias", "recibida",   "Reverso Giro",         "chile"),
    ("transferencias", "recibida",   "Depósito en Efectivo", "chile"),
    ("transferencias", "recibida",   "Dep Efect",            "chile"),
    ("transferencias", "recibida",   "Transf de",            "chile"),
    ("transferencias", "recibida",   "REMESA",               "españa"),
    ("transferencias", "recibida",   "Nium",                 "españa"),
    ("transferencias", "recibida",   "Ingreso Anonimo",      "españa"),

    ("transferencias", "conversion", "Conversión de divisas","global66"),

    # Ingresos laborales — analizar sueldos por empresa y comparar con Europa
    ("transferencias", "ingreso_laboral", "REMUNERACION",          "chile"),
    ("transferencias", "ingreso_laboral", "Remuneraciones",        "chile"),
    ("transferencias", "ingreso_laboral", "PRICEWATERH",           "chile"),

    # Seguro de cesantía AFC
    ("transferencias", "ingreso_cesantia", "0776016489",  "chile"),
    ("transferencias", "ingreso_cesantia", "AFC",          "chile"),
    ("transferencias", "ingreso_cesantia", "CESANTIA",     "chile"),

    # Apoyo familiar — seguimiento transferencias del padre
    ("transferencias", "apoyo_familiar",  "JUAN ANTONIO SOCIAS",  "chile"),
    ("transferencias", "apoyo_familiar",  "Juan antonio socias",  "global66"),

    # Devoluciones del Estado
    ("transferencias", "devolucion_impuesto", "PAGO PROVEEDOR TESORERIA", "chile"),
    ("transferencias", "devolucion_impuesto", "TESORERIA G",              "chile"),
    ("transferencias", "devolucion_impuesto", "00762091712 REEMBOLSO",    "chile"),

    # ── COMERCIO ──────────────────────────────────────────────────────────────
    ("comercio", "hogar",            "SODIMAC",              "chile"),
    ("comercio", "hogar",            "PAPELARIA FALABELLA",  "chile"),
    ("comercio", "hogar",            "FALABELLA",            "chile"),
    ("comercio", "hogar",            "IKEA",                "todas"),
    ("comercio", "hogar",            "REDELCO",             "chile"),
    ("comercio", "hogar",            "CASA IDEAS",          "chile"),
    ("comercio", "hogar",            "EASY COSTANERA",       "chile"),

    ("comercio", "electronica",   "SAMSUNGELECTRONIC",       "chile"),

    ("comercio", "entradas_ocio",    "Ticketplus Im30",      "españa"),
    ("comercio", "entradas_ocio",    "KARTING",              "chile"),
    ("comercio", "entradas_ocio",    "CINE HOYTS",           "chile"),

    ("comercio",     "outdoor_ropa",  "KOMAX",                "chile"),
    ("comercio",     "outdoor_ropa",  "GOODPEOPLE",           "chile"),
    ("comercio",     "outdoor_ropa",  "BIC PARQUE",           "chile"),
    ("comercio",     "outdoor_ropa",  "WILDLAMA",             "chile"),
    ("comercio",     "outdoor_ropa", "ANDESGEAR",             "chile"),
    ("comercio",     "ropa",         "BESTIAS",               "chile"),
    ("comercio",     "outdoor_ropa", "PATAGONIA COSTANERA",   "chile"),
    ("comercio",     "ropa",         "MOW 1",                 "chile"),

    ("comercio", "otros_comercio",   "FRANCISCO NOGUERA",    "chile"),
    ("comercio", "otros_comercio",   "SOCIEDAD COMERCIAL",   "chile"),
    ("comercio", "otros_comercio",   "VILLAR",               "chile"),
    ("comercio", "otros_comercio",   "MAYNE",                "chile"),
    ("comercio", "otros_comercio",   "Compra Nacional",      "chile"),
    ("comercio", "otros_comercio",   "Compra Intern",        "chile"),
    ("comercio", "otros_comercio",     "40627SBX",           "chile"),
    ("comercio", "otros_comercio",     "VILLA A.PENABLANCA", "chile"),
    ("comercio", "otros_comercio",     "SERVICIOS Y COMERCIAL RAU", "chile"),
    ("comercio", "otros_comercio",     "40196 MANTAGUA",    "chile"),
    ("comercio", "otros_comercio",     "CV 9017",           "chile"),
    ("comercio", "otros_comercio",     "APOQUINDO 4",       "chile"),
    ("comercio", "otros_comercio",     "JOSEFINA EDWARD",   "chile"),
    ("comercio", "otros_comercio",     "20648 TALCA",       "chile"),
    ("comercio", "otros_comercio",      "TEMU",             "todas"),
    ("comercio", "otros_comercio",      "LAS CONDES",       "chile"),
    ("comercio", "otros_comercio", "COMERCIAL LUEZAS",       "chile"),
    ("comercio", "otros_comercio", "COMERCIAL MAHO",         "chile"),
    ("comercio", "otros_comercio", "CRISTIAN ALEJANDRO",     "chile"),
    ("comercio", "otros_comercio", "ROBERTO CABELLO",        "chile"),
    ("comercio", "otros_comercio", "SUMUP C*ALEJANDRA",      "chile"),
    ("comercio", "otros_comercio", "MALL SPORT",             "chile"),
    ("comercio", "otros_comercio", "AFILA PARQUE ARAUCO",    "chile"),


    ("comercio", "entradas_ocio", "BOLETERIA WEB", "chile"),
    ("comercio", "entradas_ocio", "TICKET MASTER", "chile"),
    ("comercio", "entradas_ocio", "PUNTO TICKET", "chile"),
    ("comercio", "entradas_ocio", "LIVETICKETS", "chile"),
    ("comercio", "entradas_ocio", "RENTAL C16", "chile"),
    ("comercio", "entradas_ocio", "RENTAL WEAR", "chile"),
    ("comercio", "entradas_ocio", "CASCADA DE LAS ANIMAS", "chile"),
    ("comercio", "entradas_ocio", "PARQUE TRICAO",           "chile"),
    ("comercio", "entradas_ocio", "RECORRIDO",               "chile"),


]

# ── Filtros de líneas a ignorar ────────────────────────────────────────────────
# Estas descripciones son separadores o ruido del Excel, no movimientos reales
IGNORAR = [
    "**************************************************",
    "DESCRIPCIÓN",
    "DETALLE DE MOVIMIENTOS",
]


def crear_tabla_categorias():
    df = pd.DataFrame(CATEGORIAS, columns=[
        "categoria_padre", "subcategoria", "palabra_clave", "fuente"
    ])

    engine = create_engine(DB_PATH)
    df.to_sql("categorias", engine, if_exists="replace", index=False)

    # Guardar también los filtros de ignorar
    df_ignorar = pd.DataFrame(IGNORAR, columns=["patron"])
    df_ignorar.to_sql("ignorar_patrones", engine, if_exists="replace", index=False)

    print("="*55)
    print("Tabla de categorías creada")
    print("="*55)
    print(f"\nTotal palabras clave: {len(df)}")
    print(f"\nCategorías padre:")
    resumen = df.groupby("categoria_padre")["subcategoria"].nunique()
    for padre, n_sub in resumen.items():
        n_palabras = len(df[df["categoria_padre"] == padre])
        print(f"  {padre:<20} {n_sub} subcategorías  |  {n_palabras} palabras clave")

    print(f"\nPor fuente:")
    for fuente, n in df.groupby("fuente").size().items():
        print(f"  {fuente:<12} {n} palabras clave")

    print(f"\nBase de datos: {BASE_DIR / 'finanzas.db'}")
    print("\nAhora ejecuta: python src/recategorizar.py")


if __name__ == "__main__":
    crear_tabla_categorias()
