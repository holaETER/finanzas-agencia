import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.set_page_config(page_title="Finanzas Agencia", page_icon="📈", layout="wide")

# Conexión limpia con Supabase
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
        # Clasificaciones exactas del Estado de Resultados
        clasificacion = st.selectbox("Clasificación", [
            "Gastos administrativos", 
            "Gastos de operación", 
            "Gastos de marketing y publicidad",
            "Costos de ventas",
            "Gastos financieros"
        ])
        servicio = st.text_input("Servicio / Concepto", placeholder="Honorarios, Capcut, Google One, Comisiones...")
        proveedor = st.text_input("Proveedor", placeholder="Pamela Gracia, Ivet Hernandez, Canva, Banco...")
    
    with col2:
        total_ingresado = st.number_input("Monto Total Pagado (con IVA incluido)", min_value=0.0, step=100.0, format="%.2f")
        
        if total_ingresado > 0:
            subtotal_calc = round(total_ingresado / 1.16, 2)
            iva_calc = round(total_ingresado - subtotal_calc, 2)
            st.info(f"💡 **Desglose:** Subtotal: **${subtotal_calc:,.2f}** | IVA (16%): **${iva_calc:,.2f}** | Total: **${total_ingresado:,.2f}**")
        else:
            subtotal_calc = 0.0
            iva_calc = 0.0
            
        metodo = st.selectbox("Método de Pago", ["TRANSFERENCIA", "TD", "Efectivo", "Cargo automático"])
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
                st.success(f"✅ Gasto guardado: Total ${total_ingresado:,.2f} MXN")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
        else:
            st.error("Por favor completa los campos principales.")

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
                try:
                    supabase.table("cobranza").insert(data_c).execute()
                    st.success("Factura registrada.")
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
# TAB 3: ESTADO DE RESULTADOS (P&L EXACTO)
# ==============================
with tab3:
    st.subheader("Estado de Resultados Oficial")
    
    # 1. Controles Superiores: Ventas del Mes
    col_pnl1, col_pnl2 = st.columns([1, 1])
    with col_pnl1:
        # Permite ingresar las Ventas Netas del periodo
        ventas_netas = st.number_input("Ventas Netas del Periodo ($ MXN):", min_value=0.0, value=290700.00, step=1000.0)
    with col_pnl2:
        st.info("💡 Los gastos se calculan y clasifican automáticamente en tiempo real con lo que capturas en la Tab 1.")

    try:
        res_egresos = supabase.table("egresos").select("*").execute()
        df_eg = pd.DataFrame(res_egresos.data) if res_egresos.data else pd.DataFrame()

        # Calcular sumas por clasificación
        def obtener_total_clasif(clasif_nombre):
            if df_eg.empty or "clasificacion" not in df_eg.columns:
                return 0.0
            filtro = df_eg[df_eg["clasificacion"].str.strip().str.lower() == clasif_nombre.lower()]
            return float(filtro["total_neto"].sum())

        costo_ventas = obtener_total_clasif("Costos de ventas")
        gastos_operacion = obtener_total_clasif("Gastos de operación")
        gastos_marketing = obtener_total_clasif("Gastos de marketing y publicidad")
        gastos_admin = obtener_total_clasif("Gastos administrativos")
        gastos_financieros = obtener_total_clasif("Gastos financieros")

        # Fórmulas idénticas a tu formato
        utilidad_bruta = ventas_netas - costo_ventas
        utilidad_operacion = utilidad_bruta - (gastos_operacion + gastos_marketing + gastos_admin)
        utilidad_antes_impuestos = utilidad_operacion - gastos_financieros
        
        # ISR al 30% (solo aplica si hay utilidad)
        isr_30 = round(utilidad_antes_impuestos * 0.30, 2) if utilidad_antes_impuestos > 0 else 0.0
        iva_pnl = 0.0 # Se mantiene informativo según tu formato
        
        utilidad_neta = utilidad_antes_impuestos - isr_30
        rentabilidad = round((utilidad_neta / ventas_netas * 100), 2) if ventas_netas > 0 else 0.0

        # Construcción visual de la tabla idéntica a tu formato
        pnl_data = [
            {"Concepto": "Ventas Netas", "Parcial": None, "Total": f"${ventas_netas:,.2f}"},
            {"Concepto": "Costos de ventas", "Parcial": None, "Total": f"${costo_ventas:,.2f}"},
            {"Concepto": "UTILIDAD BRUTA", "Parcial": None, "Total": f"${utilidad_bruta:,.2f}"},
            {"Concepto": "  - Gastos de operación", "Parcial": f"${gastos_operacion:,.2f}", "Total": None},
            {"Concepto": "  - Gastos de marketing y publicidad", "Parcial": f"${gastos_marketing:,.2f}", "Total": None},
            {"Concepto": "  - Gastos Administrativos", "Parcial": f"${gastos_admin:,.2f}", "Total": None},
            {"Concepto": "UTILIDAD DE OPERACIÓN", "Parcial": None, "Total": f"${utilidad_operacion:,.2f}"},
            {"Concepto": "  - Gastos financieros", "Parcial": f"${gastos_financieros:,.2f}", "Total": None},
            {"Concepto": "UTILIDAD ANTES DE IMPUESTOS", "Parcial": None, "Total": f"${utilidad_antes_impuestos:,.2f}"},
            {"Concepto": "  - ISR (30%)", "Parcial": None, "Total": f"${isr_30:,.2f}"},
            {"Concepto": "  - IVA 16%", "Parcial": None, "Total": f"${iva_pnl:,.2f}"},
            {"Concepto": "UTILIDAD NETA (Después de impuestos)", "Parcial": None, "Total": f"${utilidad_neta:,.2f}"},
            {"Concepto": "RENTABILIDAD", "Parcial": None, "Total": f"{rentabilidad:.1f}%"}
        ]

        df_pnl = pd.DataFrame(pnl_data).fillna("")
        
        # Tarjetas de resumen arriba
        c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
        c_kpi1.metric("Ventas Netas", f"${ventas_netas:,.2f}")
        c_kpi2.metric("Utilidad Neta", f"${utilidad_neta:,.2f}", delta=f"{rentabilidad:.1f}%")
        c_kpi3.metric("Rentabilidad", f"{rentabilidad:.1f}%")

        st.markdown("### Estado de Resultados")
        st.dataframe(df_pnl, use_container_width=True, hide_index=True)

    except Exception as e:
        st.warning(f"Aviso en Estado de Resultados: {e}")
