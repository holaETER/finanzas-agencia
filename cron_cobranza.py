import os
import sys
import requests
from urllib.parse import urlparse
from datetime import date, datetime
from supabase import create_client

# 1. Credenciales limpias
raw_supabase_url = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
META_PHONE_ID = os.environ.get("META_PHONE_ID", "").strip()
META_WA_TOKEN = os.environ.get("META_WA_TOKEN", "").strip()

if not raw_supabase_url or not SUPABASE_KEY:
    print("❌ ERROR: Faltan credenciales de Supabase.")
    sys.exit(1)

if not META_PHONE_ID or not META_WA_TOKEN:
    print("❌ ERROR: Faltan credenciales de Meta.")
    sys.exit(1)

parsed = urlparse(raw_supabase_url)
SUPABASE_URL = f"{parsed.scheme}://{parsed.netloc}"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def formatear_numero_mexico(telefono):
    # Quitar signos, espacios y guiones
    num = str(telefono).replace("+", "").replace(" ", "").replace("-", "").strip()
    
    # Si viene con 10 dígitos (ej. 8128244165), agregar 521
    if len(num) == 10:
        return "521" + num
    # Si viene con 52 y 10 dígitos (ej. 528128244165), insertar el 1
    if len(num) == 12 and num.startswith("52"):
        return "521" + num[2:]
        
    return num

def enviar_whatsapp(telefono, mensaje):
    numero_destino = formatear_numero_mexico(telefono)
    url = f"https://graph.facebook.com/v19.0/{META_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_WA_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": mensaje}
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 200, response.text, numero_destino
    except Exception as e:
        return False, str(e), numero_destino

def ejecutar_cobranza():
    hoy = date.today()
    print(f"--- Iniciando revisión de cobranza a fecha: {hoy} ---")
    
    try:
        res = supabase.table("cobranza").select("*").eq("status", "Pendiente").execute()
        cuentas = res.data if res.data else []
    except Exception as e:
        print(f"❌ Error al consultar Supabase: {e}")
        return

    if not cuentas:
        print("ℹ️ No hay facturas con status 'Pendiente'.")
        return

    for item in cuentas:
        try:
            cliente = item.get("cliente", "Cliente")
            f_venc = item.get("fecha_vencimiento")
            
            if not f_venc:
                continue

            vencimiento = datetime.strptime(str(f_venc), "%Y-%m-%d").date()
            dias_restantes = (vencimiento - hoy).days
            concepto = item.get("concepto", "Servicios de Agencia")
            monto = f"${float(item.get('monto_total', 0)):,.2f} MXN"
            telefono = item.get("telefono_whatsapp", "")

            if not telefono:
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

            if mensaje:
                exito, respuesta, num_envio = enviar_whatsapp(telefono, mensaje)
                if exito:
                    supabase.table("cobranza").update({"ultimo_recordatorio": str(hoy)}).eq("id", item["id"]).execute()
                    print(f"✅ Notificación enviada con éxito a {cliente} al número: +{num_envio}")
                else:
                    print(f"❌ Error al enviar a {cliente}: {respuesta}")

        except Exception as err:
            print(f"⚠️ Error procesando {item.get('cliente')}: {err}")

if __name__ == "__main__":
    ejecutar_cobranza()
