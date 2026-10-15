import os
import requests
from datetime import date, datetime
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
META_PHONE_ID = os.environ.get("META_PHONE_ID", "").strip()
META_WA_TOKEN = os.environ.get("META_WA_TOKEN", "").strip()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def enviar_whatsapp(telefono, mensaje):
    # Asegurar que el número no tenga espacios ni guiones
    numero_limpio = telefono.replace("+", "").replace(" ", "").replace("-", "")
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
    response = requests.post(url, json=payload, headers=headers)
    return response.status_code == 200, response.text

def ejecutar_cobranza():
    hoy = date.today()
    print(f"--- Iniciando revisión de cobranza: {hoy} ---")
    
    # Consultar facturas con estatus Pendiente
    res = supabase.table("cobranza").select("*").eq("status", "Pendiente").execute()
    cuentas = res.data if res.data else []
    
    if not cuentas:
        print("No hay cobros pendientes el día de hoy.")
        return

    for item in cuentas:
        # Evitar enviar más de un recordatorio el mismo día
        if item.get("ultimo_recordatorio") == str(hoy):
            continue

        vencimiento = datetime.strptime(item["fecha_vencimiento"], "%Y-%m-%d").date()
        dias_restantes = (vencimiento - hoy).days
        cliente = item.get("cliente", "")
        concepto = item.get("concepto", "")
        monto = f"${float(item.get('monto_total', 0)):,.2f} MXN"
        telefono = item.get("telefono_whatsapp", "")

        mensaje = None

        # 1. Preventivo: 3 días antes del vencimiento
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
                f"por {monto}.\n\nQuedamos atentos al envío de tu comprobante para aplicarlo a tu cuenta. ¡Excelente día!"
            )
        # 3. Mora temprana: 3 días después de vencido
        elif dias_restantes == -3:
            mensaje = (
                f"Estimado {cliente}, notamos que la factura de '{concepto}' por {monto} presenta 3 días de vencimiento. "
                f"¿Nos apoyas confirmando si tuviste algún inconveniente con la transferencia para darte seguimiento?"
            )

        if mensaje:
            exito, respuesta = enviar_whatsapp(telefono, mensaje)
            if exito:
                supabase.table("cobranza").update({"ultimo_recordatorio": str(hoy)}).eq("id", item["id"]).execute()
                print(f"✅ Notificación enviada a {cliente} ({telefono})")
            else:
                print(f"❌ Error al enviar a {cliente}: {respuesta}")

if __name__ == "__main__":
    ejecutar_cobranza()
