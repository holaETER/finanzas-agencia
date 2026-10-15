import os
import sys
import requests
from urllib.parse import urlparse
from datetime import date, datetime
from supabase import create_client

# 1. Obtener y limpiar automáticamente la URL de Supabase
raw_supabase_url = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
META_PHONE_ID = os.environ.get("META_PHONE_ID", "").strip()
META_WA_TOKEN = os.environ.get("META_WA_TOKEN", "").strip()

if not raw_supabase_url or not SUPABASE_KEY:
    print("❌ ERROR: Falta configurar SUPABASE_URL o SUPABASE_KEY en los Secrets de GitHub.")
    sys.exit(1)

if not META_PHONE_ID or not META_WA_TOKEN:
    print("❌ ERROR: Falta configurar META_PHONE_ID o META_WA_TOKEN en los Secrets de GitHub.")
    sys.exit(1)

# Esta línea corta cualquier '/rest/v1' o diagonal y deja solo 'https://xxxx.supabase.co'
parsed = urlparse(raw_supabase_url)
SUPABASE_URL = f"{parsed.scheme}://{parsed.netloc}"

print(f"✅ Conectando a Supabase en: {SUPABASE_URL}")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def enviar_whatsapp(telefono, mensaje):
    numero_limpio = str(telefono).replace("+", "").replace(" ", "").replace("-", "")
    url = f"https://graph.facebook.com/v19.0/{META_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_WA_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_limpio,
        "type": "text",
        "text": {"body": mensaje}
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

def ejecutar_cobranza():
    hoy = date.today()
    print(f"--- Iniciando revisión de cobranza a fecha: {hoy} ---")
    
    try:
        res = supabase.table("cobranza").select("*").eq("status", "Pendiente").execute()
        cuentas = res.data if res.data else []
    except Exception as e:
        print(f"❌ Error al consultar tabla cobranza: {e}")
        return

    if not cuentas:
        print("ℹ️ No hay facturas con status 'Pendiente' el día de hoy.")
        return

    print(f"📋 Se encontraron {len(cuentas)} factura(s) pendiente(s).")

    for item in cuentas:
        try:
            cliente = item.get("cliente", "Cliente")
            f_venc = item.get("fecha_vencimiento")
            
            if not f_venc:
                print(f"⚠️ Saltando ID {item.get('id')} ({cliente}): sin fecha de vencimiento.")
                continue

            if item.get("ultimo_recordatorio") == str(hoy):
                print(f"ℹ️ {cliente} ya fue notificado el día de hoy.")
                continue

            vencimiento = datetime.strptime(str(f_venc), "%Y-%m-%d").date()
            dias_restantes = (vencimiento - hoy).days
            concepto = item.get("concepto", "Servicios de Agencia")
            monto = f"${float(item.get('monto_total', 0)):,.2f} MXN"
            telefono = item.get("telefono_whatsapp", "")

            if not telefono:
                print(f"⚠️ Saltando {cliente}: sin teléfono registrado.")
                continue

            mensaje = None

            # 1. Preventivo: 3 días antes
            if dias_restantes == 3:
                mensaje = (
                    f"Hola {cliente}, gusto en saludarte. Te recordamos cordialmente que tu servicio '{concepto}' "
                    f"por un monto de {monto} vence en 3 días ({vencimiento.strftime('%d/%m/%Y')}).\n\n"
                    f"Datos para transferencia:\nBanco Bajío | CLABE: 030XXXXXXXXXXX\n\n¡Muchas gracias!"
                )
            # 2. Día de vencimiento (Hoy)
            elif dias_restantes == 0:
                mensaje = (
                    f"Hola {cliente}, te recordamos que el día de hoy vence tu pago correspondiente a '{concepto}' "
                    f"por {monto}.\n\nQuedamos atentos al envío de tu comprobante. ¡Excelente día!"
                )
            # 3. Mora temprana: 3 días después
            elif dias_restantes == -3:
                mensaje = (
                    f"Estimado {cliente}, notamos que la factura de '{concepto}' por {monto} presenta 3 días de vencimiento. "
                    f"¿Nos apoyas confirmando si tuviste algún inconveniente con la transferencia?"
                )
            else:
                print(f"ℹ️ {cliente}: Faltan {dias_restantes} días para el vencimiento (no requiere mensaje hoy).")

            if mensaje:
                print(f"📤 Enviando recordatorio a {cliente} ({telefono})...")
