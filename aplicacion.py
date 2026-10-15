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

tab1, tab2, tab3, tab4 = st.tabs([
    "➕ Captura de Egresos", 
    "💵 Captura de Ingresos", 
    "📲 Clientes y Cobranza", 
    "📊 Estado de Resultados"
])

# ==============================
# TAB 1: REGISTRO DE EGRESOS
# ==============================
with tab1:
    st.subheader("Registrar Nuevo Gasto")
    col1, col2 = st.columns(2)
    with col1:
        fecha_eg = st.date_input("Fecha de pago", date.today(), key="f_eg")
        clasificacion = st.selectbox("Clasificación", [
            "Gastos administrativos", 
            "Gastos de operación", 
            "Gastos de marketing y publicidad",
            "Costos de ventas",
            "Gastos financieros"
        ])
        servicio = st.text_input("Servicio / Concepto", placeholder="Honorarios, Capcut, Google One, Telcel...")
        proveedor = st.text_input("Proveedor", placeholder="Pamela Gracia, Ivet Hernandez, Canva...")
    
    with col2:
        total_egreso = st.number_input("Monto Total Pagado (con IVA)", min_value=0.0, step=100.0, format="%.2f", key="tot_eg")
        if total_egreso > 0:
            sub_eg = round(total_egreso / 1.16, 2)
            iva_eg = round(total_egreso - sub_eg, 2)
            st.info(f"💡 Subtotal: **${sub_eg:,.2f}** | IVA (16%): **${iva_eg:,.2f}**")
        else:
            sub_eg, iva_eg = 0.0, 0.0
            
        metodo_eg = st.selectbox("Método de Pago", ["TRANSFERENCIA", "TD", "Efectivo", "Cargo automático"], key="met_eg")
        banco_eg = st.selectbox("Banco / Cuenta", ["BAJIO", "Azteca", "Cuenta Ivet", "Otro"], key="ban_eg")
        comentarios_eg = st.text_input("Comentarios", placeholder="Opcional", key="com_eg")

    if st.button("💾 Guardar Egreso", type="primary", use_container_width=True):
        if total_egreso > 0 and servicio and proveedor:
            data = {
                "fecha": str(fecha_eg),
                "clasificacion": clasificacion,
                "servicio_producto": servicio,
                "proveedor": proveedor,
                "subtotal": sub_eg,
                "iva": iva_eg,
                "total_neto": total_egreso,
                "metodo_pago": metodo_eg,
                "banco_origen": banco_eg,
                "status": "Pagado",
                "comentarios": comentarios_eg
            }
            try:
                supabase.table("egresos").insert(data).execute()
                st.success(f"✅ Gasto guardado: Total ${total_egreso:,.2f} MXN")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
        else:
            st.error("Completa servicio, proveedor y total.")

# ==============================
# TAB 2: REGISTRO DE INGRESOS
# ==============================
with tab2:
    st.subheader("Registrar Nuevo Ingreso de Cliente")
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        fecha_in = st.date_input("Fecha de depósito", date.today(), key="f_in")
        nombre_cliente = st.text_input("Nombre del Cliente", placeholder="Ej. Georges Jarjoura, Carlos Quiroz...")
        empresa = st.text_input("Empresa / Proyecto", placeholder="Ej. SULTAN, ONTRACK, CAFFI...")
        rfc = st.text_input("RFC", placeholder="Opcional")

    with col_in2:
        total_ingreso = st.number_input("Total Recibido ($ MXN)", min_value=0.0, step=500.0, format="%.2f", key="tot_in")
        if total_ingreso > 0:
            sub_in = round(total_ingreso / 1.16, 2)
            iva_in = round(total_ingreso - sub_in, 2)
            st.info(f"💡 Subtotal: **${sub_in:,.2f}** | IVA (16%): **${iva_in:,.2f}**")
        else:
            sub_in, iva_in = 0.0, 0.0
            
        metodo_in = st.selectbox("Método de Pago", ["TRANSFERENCIA", "DEPOSITO", "Efectivo"], key="met_in")
        status_in = st.selectbox("Status", ["PAGADO", "PENDIENTE"], key="st_in")

    if st.button("💾 Guardar Ingreso", type="primary", use_container_width=True):
        if total_ingreso > 0 and nombre_cliente:
            data_in = {
                "fecha": str(fecha_in),
                "nombre_cliente": nombre_cliente,
                "rfc": rfc,
                "subtotal": sub_in,
                "iva": iva_in,
                "total_neto": total_ingreso,
                "status": status_in,
                "metodo_pago": metodo_in,
                "empresa": empresa
            }
            try:
                supabase.table("ingresos").insert(data_in).execute()
                st.success(f"✅ Ingreso registrado con éxito: ${total_ingreso:,.2f} MXN")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar ingreso: {e}")
        else:
            st.error("Completa el nombre del cliente y el monto.")

# ==============================
# TAB 3: COBRANZA
# ==============================
with tab3:
    st.subheader("Control de Cobranza (WhatsApp)")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown("**Nuevo Cobro a Cliente**")
        with st.form("form_cobranza", clear_on_submit=True):
            cliente_cob = st.text_input("Nombre del Cliente")
            telefono_cob = st.text_input("WhatsApp (ej. +5215512345678)")
            concepto_cob = st.text_input("Concepto de Factura", placeholder="Retainer mensual...")
            monto_cob = st.number_input("Monto a cobrar ($)", min_value=0.0, step=500.0)
            vencimiento_cob = st.date_input("Fecha de Vencimiento")
            
            submit_cobranza = st.form_submit_button("Registrar Cobro")
            if submit_cobranza and cliente_cob and telefono_cob and monto_cob > 0:
                data_c = {
                    "cliente": cliente_cob,
                    "telefono_whatsapp": telefono_cob,
                    "concepto": concepto_cob,
                    "monto_total": monto_cob,
                    "fecha_vencimiento": str(vencimiento_cob),
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
# TAB 4: ESTADO DE RESULTADOS (AUTOMATIZADO)
# ==============================
with tab4:
    st.subheader("Estado de Resultados Automático")
    
    MESES_DICT = {
        "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
        "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
        "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
    }

    try:
        res_eg = supabase.table("egresos").select("*").execute()
        res_in = supabase.table("ingresos").select("*").execute()
        
        df_eg = pd.DataFrame(res_eg.data) if res_eg.data else pd.DataFrame()
        df_in = pd.DataFrame(res_in.data) if res_in.data else pd.DataFrame()

        # Preparar periodos
        todos_periodos = set()
        if not df_eg.empty:
            df_eg["fecha_dt"] = pd.to_datetime(df_eg["fecha"])
            df_eg["periodo_clave"] = df_eg["fecha_dt"].dt.strftime("%Y-%m")
            todos_periodos.update(df_eg["periodo_clave"].unique())
            
        if not df_in.empty:
            df_in["fecha_dt"] = pd.to_datetime(df_in["fecha"])
            df_in["periodo_clave"] = df_in["fecha_dt"].dt.strftime("%Y-%m")
            todos_periodos.update(df_in["periodo_clave"].unique())

        periodos_ordenados = sorted(list(todos_periodos), reverse=True)
        opciones_meses = ["Histórico Completo (Acumulado)"]
        mapa_etiquetas = {}
        for p in periodos_ordenados:
            anio, mes = p.split("-")
            nombre_label = f"{MESES_DICT.get(mes, mes)} {anio}"
            opciones_meses.append(nombre_label)
            mapa_etiquetas[nombre_label] = p

        # Filtros
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            mes_sel = st.selectbox("📅 Selecciona el Mes a Evaluar:", opciones_meses)
            
        # Filtrado de DataFrames
        if mes_sel == "Histórico Completo (Acumulado)":
            df_eg_f = df_eg
            df_in_f = df_in
            titulo_p = "Histórico Acumulado 2026"
        else:
            clave_p = mapa_etiquetas[mes_sel]
            df_eg_f = df_eg[df_eg["periodo_clave"] == clave_p] if not df_eg.empty else pd.DataFrame()
            df_in_f = df_in[df_in["periodo_clave"] == clave_p] if not df_in.empty else pd.DataFrame()
            titulo_p = mes_sel

        # CÁLCULO DE VENTAS NETAS AUTOMÁTICAS (Solo lo Pagado)
        ventas_automaticas = 0.0
        if not df_in_f.empty and "status" in df_in_f.columns:
            ventas_automaticas = float(df_in_f[df_in_f["status"] == "PAGADO"]["total_neto"].sum())

        with col_f2:
            gastos_fin = st.number_input("Gastos Financieros / Comisiones ($):", min_value=0.0, value=0.0, step=100.0)

        # CÁLCULO DE EGRESOS POR CLASIFICACIÓN
        def sum_eg(clasif_nombre):
            if df_eg_f.empty or "clasificacion" not in df_eg_f.columns:
                return 0.0
            filtro = df_eg_f[df_eg_f["clasificacion"].str.strip().str.lower() == clasif_nombre.lower()]
            return float(filtro["total_neto"].sum())

        costo_ventas = sum_eg("Costos de ventas")
        gastos_operacion = sum_eg("Gastos de operación")
        gastos_marketing = sum_eg("Gastos de marketing y publicidad")
        gastos_admin = sum_eg("Gastos administrativos")
        total_gastos_financieros = sum_eg("Gastos financieros") + gastos_fin

        # FÓRMULAS
        utilidad_bruta = ventas_automaticas - costo_ventas
        utilidad_operacion = utilidad_bruta - (gastos_operacion + gastos_marketing + gastos_admin)
        utilidad_antes_impuestos = utilidad_operacion - total_gastos_financieros
        isr_30 = round(utilidad_antes_impuestos * 0.30, 2) if utilidad_antes_impuestos > 0 else 0.0
        utilidad_neta = utilidad_antes_impuestos - isr_30
        rentabilidad = round((utilidad_neta / ventas_automaticas * 100), 2) if ventas_automaticas > 0 else 0.0

        # KPI CARDS
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Ventas Netas (Cobrado)", f"${ventas_automaticas:,.2f}")
        k2.metric("Total Gastos", f"${(costo_ventas + gastos_operacion + gastos_marketing + gastos_admin + total_gastos_financieros):,.2f}")
        k3.metric("Utilidad Neta", f"${utilidad_neta:,.2f}")
        k4.metric("Rentabilidad", f"{rentabilidad:.1f}%")

        # TABLA ESTADO DE RESULTADOS
        pnl_data = [
            {"Concepto": "Ventas Netas (Ingresos Pagados)", "Parcial": "", "Total": f"${ventas_automaticas:,.2f}"},
            {"Concepto": "Costos de ventas", "Parcial": "", "Total": f"${costo_ventas:,.2f}"},
            {"Concepto": "UTILIDAD BRUTA", "Parcial": "", "Total": f"${utilidad_bruta:,.2f}"},
            {"Concepto": "  - Gastos de operación", "Parcial": f"${gastos_operacion:,.2f}", "Total": ""},
            {"Concepto": "  - Gastos de marketing y publicidad", "Parcial": f"${gastos_marketing:,.2f}", "Total": ""},
            {"Concepto": "  - Gastos Administrativos", "Parcial": f"${gastos_admin:,.2f}", "Total": ""},
            {"Concepto": "UTILIDAD DE OPERACIÓN", "Parcial": "", "Total": f"${utilidad_operacion:,.2f}"},
            {"Concepto": "  - Gastos financieros", "Parcial": f"${total_gastos_financieros:,.2f}", "Total": ""},
            {"Concepto": "UTILIDAD ANTES DE IMPUESTOS", "Parcial": "", "Total": f"${utilidad_antes_impuestos:,.2f}"},
            {"Concepto": "  - ISR (30%)", "Parcial": "", "Total": f"${isr_30:,.2f}"},
            {"Concepto": "  - IVA 16%", "Parcial": "", "Total": "$0.00"},
            {"Concepto": "UTILIDAD NETA", "Parcial": "", "Total": f"${utilidad_neta:,.2f}"},
            {"Concepto": "RENTABILIDAD", "Parcial": "", "Total": f"{rentabilidad:.1f}%"}
        ]
        
        st.markdown(f"### Estado de Resultados: **{titulo_p}**")
        st.dataframe(pd.DataFrame(pnl_data), use_container_width=True, hide_index=True)

        # TABLAS DE DETALLE
        subtab1, subtab2 = st.tabs(["💵 Ingresos del Mes", "💳 Egresos del Mes"])
        with subtab1:
            if not df_in_f.empty:
                cols_in = [c for c in ["fecha", "nombre_cliente", "empresa", "subtotal", "iva", "total_neto", "metodo_pago", "status"] if c in df_in_f.columns]
                st.dataframe(df_in_f[cols_in], use_container_width=True, hide_index=True)
            else:
                st.caption("No hay ingresos registrados para este periodo.")

        with subtab2:
            if not df_eg_f.empty:
                cols_eg = [c for c in ["fecha", "clasificacion", "servicio_producto", "proveedor", "total_neto", "metodo_pago", "banco_origen", "comentarios"] if c in df_eg_f.columns]
                st.dataframe(df_eg_f[cols_eg], use_container_width=True, hide_index=True)
            else:
                st.caption("No hay egresos registrados para este periodo.")

    except Exception as e:
        st.warning(f"Aviso en Estado de Resultados: {e}")
