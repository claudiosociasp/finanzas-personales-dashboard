#!/usr/bin/env python3
"""
Script maestro de actualización mensual
Claudio Socias Paradiz — Finanzas Personales

Ejecuta en orden:
  1. Tipo de cambio CLP/EUR
  2. Datos de mercado (IPC, alquiler, salarios)
  3. ETL cuenta corriente
  4. ETL tarjeta de crédito
  5. ETL Global66 + Santander España
  6. Recategorizar
  7. Generar DB demo
  8. Git push
  9. Deploy en Render

Uso:
    cd ~/Desktop/finanzas_personales
    source venv/bin/activate
    python src/actualizar.py
"""

import subprocess
import sys
import os
import time
import requests
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).parent.parent
SRC_DIR  = Path(__file__).parent

RENDER_API_KEY  = os.environ.get("RENDER_API_KEY", "rnd_JwKUNa1UtoUwTrc72Kbw8yO3qK1u")
RENDER_SERVICE  = os.environ.get("RENDER_SERVICE_ID", "srv-d7e02d8sfn5c738kps0g")

def sep(titulo):
    print(f"\n{'='*55}")
    print(f"  {titulo}")
    print(f"{'='*55}")

def run(script, descripcion):
    sep(descripcion)
    result = subprocess.run(
        [sys.executable, str(SRC_DIR / script)],
        cwd=str(BASE_DIR),
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"\n❌ Error en {script} — abortando")
        sys.exit(1)
    print(f"\n✅ {descripcion} completado")

def git_push():
    sep("Git — commit y push")
    hoy = date.today().strftime("%Y-%m-%d")
    cmds = [
        ["git", "add", "finanzas_demo.db"],
        ["git", "commit", "-m", f"data: actualización mensual {hoy}"],
        ["git", "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=False)
        if result.returncode != 0 and "nothing to commit" not in str(result.stdout):
            print(f"⚠️  Warning en: {' '.join(cmd)}")
    print("\n✅ GitHub actualizado")

def render_deploy():
    sep("Render — disparar deploy")
    url = f"https://api.render.com/v1/services/{RENDER_SERVICE}/deploys"
    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, headers=headers, json={"clearCache": "do_not_clear"})
        if resp.status_code in [200, 201]:
            deploy_id = resp.json().get("id", "—")
            print(f"  Deploy disparado: {deploy_id}")
            print(f"  URL: https://finanzas-personales-dashboard.onrender.com")
            print("\n✅ Render deploy iniciado — tardará ~2 minutos")
        else:
            print(f"⚠️  Render respondió {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"⚠️  Error conectando con Render: {e}")

def main():
    print(f"""
{'='*55}
  Actualización Mensual — Finanzas Personales
  Claudio Socias Paradiz
  Fecha: {date.today().strftime('%d/%m/%Y')}
{'='*55}
""")

    pasos = [
        ("tipo_cambio.py",                    "1/7 Tipo de cambio CLP/EUR"),
        ("actualizar_mercado.py",             "2/7 Datos de mercado"),
        ("etl_cuenta.py",                     "3/7 ETL Cuenta Corriente"),
        ("etl_tarjeta.py",                    "4/7 ETL Tarjeta de Crédito"),
        ("etl_global66_santander_españa.py",  "5/7 ETL Global66 + Santander España"),
        ("recategorizar.py",                  "6/7 Recategorizar"),
        ("generar_demo.py",                   "7/7 Generar DB demo"),
    ]

    for script, desc in pasos:
        run(script, desc)

    git_push()
    render_deploy()

    print(f"""
{'='*55}
  ✅ Actualización completada
  Dashboard: https://finanzas-personales-dashboard.onrender.com
  GitHub: https://github.com/claudiosociasp/finanzas-personales-dashboard
{'='*55}
""")

if __name__ == "__main__":
    main()
