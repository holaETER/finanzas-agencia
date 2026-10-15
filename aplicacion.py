import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.set_page_config(page_title="Finanzas Agencia", page_icon="📈", layout="wide")

# Conexión con Supabase con limpieza automática de URL
raw_url = st.secrets["SUPABASE_URL"].strip().rstrip("/")
if raw_url.endswith("/rest/v1"):
    raw_url = raw_url.replace("/rest/v1", "").rstrip("/")
SUPABASE_URL = raw_url
SUPABASE_KEY = st.secrets["SUPABASE_KEY"].strip()

@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

st.title("⚡ Finanzas en Tiempo Real")

tab1, tab2, tab3 = st.tabs(["➕ Captura de Egresos", "📲 Clientes y Cobranza", "📊 Estado de Resultados"])

# ==============================
# TAB 1: REGISTRO DE GASTOS
# ==============================
with tab1:
    st.subheader("Registrar Nuevo Gasto")
    
    col1, col2 = st.columns(2)
    with col1:
        fecha = st.date_input("Fecha de pago", date.today())
        clasificacion = st.selectbox("Clasificación", ["Gastos administrativos", "Gastos de operación"])
        servicio = st.text_input("Servicio / Concepto", placeholder="Honorarios, Capcut, Google One, Telcel...")
        proveedor = st.text_input("Proveedor", placeholder="Pamela Gracia, Ivet Hernandez, Canva...")
    
    with col2:
        # AQUÍ INGRESAS EL TOTAL DIRECTO DE TU ESTADO DE CUENTA
        total_ingresado = st.number_input("Monto Total Pagado (con IVA incluido)", min_value=0.0, step=50.0, format="%.2f")
        
        # Cálculo automático y desglose en vivo
        if total_ingresado > 0:
            subtotal_calc = round(total_ingresado / 1.16, 2)
            iva_calc = round(total_ingresado - subtotal_calc, 2)
            st.info(f"💡 **Desglose:** Subtotal: **${subtotal_calc:,.2f}** | IVA (16%): **${iva_calc:,.2f}** | Total: **${total_ingresado:,.2f}**")
        else:
            subtotal_calc = 0.0
            iva_calc = 0.0
            
        metodo = st.selectbox("Método de Pago", ["TRANSFERENCIA", "TD", "Efectivo"])
        banco = st.selectbox("Banco / Cuenta", ["BAJIO", "Azteca", "Cuenta Ivet", "Otro"])
        comentarios = st.text_input("Comentarios", placeholder="Opcional")

    if st.button("💾 Guardar Egreso en Tiempo Real", type="primary", use_container_width=True):
        if total_ingresado > 0 and servicio and proveedor:
            data = {
                "fecha": str(fecha),
                "clasificacion": clasificacion,
                "servicio_producto": servicio,
                "proveedor": proveedor,
                "subtotal": subtotal_calc,
                "iva": iva_calc,
                "total_neto": total_ingresado,
                "metodo_pago": metodo,
                "banco_origen": banco,
                "status": "Pagado",
                "comentarios": comentarios
            }
            try:
                supabase.table("egresos").insert(data).execute()
                st.success(f"✅ Gasto guardado: Total ${total_ingresado:,.2f} (Subtotal: ${subtotal_calc:,.2f} | IVA: ${iva_calc:,.2f})")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
        else:
            st.error("Por favor completa servicio, proveedor y el monto total.")

# ==============================
# TAB 2: COBRANZA
# ==============================
with tab2:
    st.subheader("Control de Cobranza (WhatsApp)")
    col_a, col_b = st.columns([1, 2])
    
    with col_a:
        st.markdown("**Nuevo Cobro a Cliente**")
        with st.form("form_cobranza", clear_on_submit=True):
            cliente = st.text_input("Nombre del Cliente")
            telefono = st.text_input("WhatsApp (ej. +5215512345678)")
            concepto_c = st.text_input("Concepto de Factura", placeholder="Retainer mensual, Campaña...")
            monto_c = st.number_input("Monto a cobrar ($)", min_value=0.0, step=500.0)
            vencimiento = st.date_input("Fecha de Vencimiento")
            
            submit_cobranza = st.form_submit_button("Registrar Cobro")
            if submit_cobranza and cliente and telefono and monto_c > 0:
                data_c = {
                    "cliente": cliente,
                    "telefono_whatsapp": telefono,
                    "concepto": concepto_c,
                    "monto_total": monto_c,
                    "fecha_vencimiento": str(vencimiento),
                    "status": "Pendiente"
                }
                try:
                    supabase.table("cobranza").insert(data_c).execute()
                    st.success("Factura registrada para cobranza.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar cobranza: {e}")

    with col_b:
        st.markdown("**Facturas Pendientes**")
        try:
            res_cobranza = supabase.table("cobranza").select("*").execute()
            if res_cobranza.data:
                df_cob = pd.DataFrame(res_cobranza.data)
                columnas_mostrar = [c for c in ["cliente", "concepto", "monto_total", "fecha_vencimiento", "status"] if c in df_cob.columns]
                st.dataframe(df_cob[columnas_mostrar], use_container_width=True)
                
                pendientes = [f"{r['id']} - {r['cliente']} (${r['monto_total']})" for r in res_cobranza.data if r.get('status') == 'Pendiente']
                if pendientes:
                    cobro_id = st.selectbox("Marcar factura como liquidada:", pendientes).split(" - ")[0]
                    if st.button("Marcar como Pagado"):
                        supabase.table("cobranza").update({"status": "Pagado"}).eq("id", cobro_id).execute()
                        st.success("¡Cobro aplicado!")
                        st.rerun()
            else:
                st.caption("No hay cobros pendientes.")
        except Exception as e:
            st.warning(f"Aviso en módulo Cobranza: {e}")

# ==============================
# TAB 3: ESTADO DE RESULTADOS (P&L)
# ==============================
with tab3:
    st.subheader("Estado de Resultados y Desglose Financiero")
    try:
        res_egresos = supabase.table("egresos").select("*").order("fecha", desc=True).execute()
        if res_egresos.data:
            df_eg = pd.DataFrame(res_egresos.data)
            
            # Formateo de números
            total_neto = df_eg["total_neto"].sum()
            subtotal_total = df_eg["subtotal"].sum()
            iva_total = df_eg["iva"].sum()
            
            # Tarjetas Principales
            c1, c2, c3 = st.columns(3)
            c1.metric("Salida Total de Efectivo", f"${total_neto:,.2f} MXN")
            c2.metric("Gasto Real Deducible (Subtotal)", f"${subtotal_total:,.2f} MXN")
            c3.metric("IVA Acreditable (a favor)", f"${iva_total:,.2f} MXN")
            
            # Resumen por Clasificación (Administrativos vs Operación)
            st.markdown("### Resumen por Clasificación")
            resumen_tipo = df_eg.groupby("clasificacion")[["subtotal", "iva", "total_neto"]].sum().reset_index()
            resumen_tipo.columns = ["Clasificación", "Subtotal (Gasto)", "IVA (16%)", "Total Neto"]
            st.dataframe(resumen_tipo.style.format({
                "Subtotal (Gasto)": "${:,.2f}",
                "IVA (16%)": "${:,.2f}",
                "Total Neto": "${:,.2f}"
            }), use_container_width=True)
            
            # Detalle completo
            st.markdown("### Historial Detallado de Egresos")
            columnas_detalle = ["fecha", "clasificacion", "servicio_producto", "proveedor", "subtotal", "iva", "total_neto", "metodo_pago", "banco_origen", "comentarios"]
            cols_existentes = [col for col in columnas_detalle if col in df_eg.columns]
            st.dataframe(df_eg[cols_existentes], use_container_width=True)
        else:
            st.info("Aún no hay transacciones registradas.")
    except Exception as e:
        st.warning(f"Aviso en Estado de Resultados: {e}")
