import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.set_page_config(page_title="Finanzas Agencia", page_icon="📈", layout="wide")

# Conexión con Supabase usando Secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

st.title("⚡ Finanzas en Tiempo Real")

tab1, tab2, tab3 = st.tabs(["➕ Captura de Egresos", "📲 Clientes y Cobranza", "📊 Estado de Resultados"])

# TAB 1: REGISTRO DE GASTOS
with tab1:
    st.subheader("Registrar Nuevo Gasto")
    with st.form("form_egreso", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            fecha = st.date_input("Fecha", date.today())
            clasificacion = st.selectbox("Clasificación", ["Gastos administrativos", "Gastos de operación"])
            servicio = st.text_input("Servicio / Concepto", placeholder="Honorarios, Capcut, Google One...")
            proveedor = st.text_input("Proveedor", placeholder="Pamela Gracia, Ivet Hernandez, Canva...")
        
        with c2:
            subtotal = st.number_input("Subtotal (sin IVA)", min_value=0.0, step=100.0, format="%.2f")
            metodo = st.selectbox("Método de Pago", ["TRANSFERENCIA", "TD", "Efectivo"])
            banco = st.selectbox("Banco / Cuenta", ["BAJIO", "Azteca", "Cuenta Ivet", "Otro"])
            comentarios = st.text_input("Comentarios", placeholder="Opcional")

        submit_egreso = st.form_submit_button("💾 Guardar Egreso")

        if submit_egreso:
            if subtotal > 0 and servicio and proveedor:
                iva = round(subtotal * 0.16, 2)
                total = round(subtotal + iva, 2)
                
                data = {
                    "fecha": str(fecha),
                    "clasificacion": clasificacion,
                    "servicio_producto": servicio,
                    "proveedor": proveedor,
                    "subtotal": subtotal,
                    "iva": iva,
                    "total_neto": total,
                    "metodo_pago": metodo,
                    "banco_origen": banco,
                    "status": "Pagado",
                    "comentarios": comentarios
                }
                supabase.table("egresos").insert(data).execute()
                st.success(f"✅ Gasto guardado con éxito. Total neto: ${total:,.2f} MXN")
                st.rerun()
            else:
                st.error("Por favor completa los campos principales.")

# TAB 2: COBRANZA
with tab2:
    st.subheader("Control de Cobranza (WhatsApp)")
    col_a, col_b = st.columns([1, 2])
    
    with col_a:
        st.markdown("**Nuevo Cobro a Cliente**")
        with st.form("form_cobranza", clear_on_submit=True):
            cliente = st.text_input("Nombre del Cliente")
            telefono = st.text_input("WhatsApp (ej. +5215512345678)")
            concepto_c = st.text_input("Concepto de Factura", placeholder="Retainer mensual...")
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
                supabase.table("cobranza").insert(data_c).execute()
                st.success("Factura registrada.")
                st.rerun()

    with col_b:
        st.markdown("**Facturas Pendientes**")
        res_cobranza = supabase.table("cobranza").select("*").order("fecha_vencimiento").execute()
        if res_cobranza.data:
            df_cob = pd.DataFrame(res_cobranza.data)
            st.dataframe(df_cob[["cliente", "concepto", "monto_total", "fecha_vencimiento", "status"]], use_container_width=True)
            
            pendientes = [f"{r['id']} - {r['cliente']} (${r['monto_total']})" for r in res_cobranza.data if r['status'] == 'Pendiente']
            if pendientes:
                cobro_id = st.selectbox("Marcar factura como liquidada:", pendientes).split(" - ")[0]
                if st.button("Marcar como Pagado"):
                    supabase.table("cobranza").update({"status": "Pagado"}).eq("id", cobro_id).execute()
                    st.success("¡Cobro aplicado!")
                    st.rerun()
        else:
            st.caption("No hay cobros pendientes.")

# TAB 3: ESTADO DE RESULTADOS
with tab3:
    st.subheader("Métricas y Resumen")
    res_egresos = supabase.table("egresos").select("*").order("fecha", desc=True).execute()
    
    if res_egresos.data:
        df_eg = pd.DataFrame(res_egresos.data)
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Egresos", f"${df_eg['total_neto'].sum():,.2f}")
        kpi2.metric("Subtotal Acumulado", f"${df_eg['subtotal'].sum():,.2f}")
        kpi3.metric("IVA Acreditable Acumulado", f"${df_eg['iva'].sum():,.2f}")
        
        st.markdown("### Historial de Egresos")
        st.dataframe(df_eg[["fecha", "clasificacion", "servicio_producto", "proveedor", "total_neto", "metodo_pago", "banco_origen", "comentarios"]], use_container_width=True)
    else:
        st.info("Aún no has registrado ningún gasto.")
