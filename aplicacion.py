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
# TAB 3: ESTADO DE RESULTADOS CON FILTRO MENSUAL
# ==============================
with tab3:
    st.subheader("Estado de Resultados Mensual y Comparativo")
    
    MESES_DICT = {
        "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
        "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
        "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
    }

    try:
        res_egresos = supabase.table("egresos").select("*").execute()
        if res_egresos.data:
            df_eg = pd.DataFrame(res_egresos.data)
            df_eg["fecha_dt"] = pd.to_datetime(df_eg["fecha"])
            df_eg["periodo_clave"] = df_eg["fecha_dt"].dt.strftime("%Y-%m")
            
            # Generar lista de meses disponibles en los datos
            periodos_unicos = sorted(df_eg["periodo_clave"].unique(), reverse=True)
            opciones_meses = ["Histórico Completo (Acumulado)"]
            
            mapa_etiquetas = {}
            for p in periodos_unicos:
                anio, mes = p.split("-")
                nombre_formato = f"{MESES_DICT.get(mes, mes)} {anio}"
                opciones_meses.append(nombre_formato)
                mapa_etiquetas[nombre_formato] = p

            # Selector de Mes en la interfaz
            col_filtro1, col_filtro2, col_filtro3 = st.columns([1.5, 1.5, 1])
            with col_filtro1:
                mes_seleccionado = st.selectbox("📅 Selecciona el Periodo / Mes:", opciones_meses)
            
            # Filtrar DataFrame según selección
            if mes_seleccionado == "Histórico Completo (Acumulado)":
                df_filtrado = df_eg
                titulo_periodo = "Histórico Acumulado 2026"
            else:
                clave_sel = mapa_etiquetas[mes_seleccionado]
                df_filtrado = df_eg[df_eg["periodo_clave"] == clave_sel]
                titulo_periodo = mes_seleccionado

            with col_filtro2:
                # Ventas del periodo seleccionado
                ventas_default = 290700.00 if mes_seleccionado in ["Enero 2026", "Histórico Completo (Acumulado)"] else 0.00
                ventas_netas = st.number_input(f"Ventas Netas ({titulo_periodo}) $:", min_value=0.0, value=ventas_default, step=1000.0)

            with col_filtro3:
                gastos_financieros_input = st.number_input("Gastos Financieros $:", min_value=0.0, value=3000.00 if mes_seleccionado in ["Enero 2026", "Histórico Completo (Acumulado)"] else 0.00, step=100.0)

            # Sumas por clasificación en el periodo filtrado
            def sum_clasif(clasif_nombre):
                if df_filtrado.empty:
                    return 0.0
                filtro = df_filtrado[df_filtrado["clasificacion"].str.strip().str.lower() == clasif_nombre.lower()]
                return float(filtro["total_neto"].sum())

            costo_ventas = sum_clasif("Costos de ventas")
            gastos_operacion = sum_clasif("Gastos de operación")
            gastos_marketing = sum_clasif("Gastos de marketing y publicidad")
            gastos_admin = sum_clasif("Gastos administrativos")
            gastos_financieros = sum_clasif("Gastos financieros") + gastos_financieros_input

            # Fórmulas del Estado de Resultados
            utilidad_bruta = ventas_netas - costo_ventas
            utilidad_operacion = utilidad_bruta - (gastos_operacion + gastos_marketing + gastos_admin)
            utilidad_antes_impuestos = utilidad_operacion - gastos_financieros
            isr_30 = round(utilidad_antes_impuestos * 0.30, 2) if utilidad_antes_impuestos > 0 else 0.0
            utilidad_neta = utilidad_antes_impuestos - isr_30
            rentabilidad = round((utilidad_neta / ventas_netas * 100), 2) if ventas_netas > 0 else 0.0

            # Tabla oficial idéntica a tu formato
            pnl_data = [
                {"Concepto": "Ventas Netas", "Parcial": "", "Total": f"${ventas_netas:,.2f}"},
                {"Concepto": "Costos de ventas", "Parcial": "", "Total": f"${costo_ventas:,.2f}"},
                {"Concepto": "UTILIDAD BRUTA", "Parcial": "", "Total": f"${utilidad_bruta:,.2f}"},
                {"Concepto": "  - Gastos de operación", "Parcial": f"${gastos_operacion:,.2f}", "Total": ""},
                {"Concepto": "  - Gastos de marketing y publicidad", "Parcial": f"${gastos_marketing:,.2f}", "Total": ""},
                {"Concepto": "  - Gastos Administrativos", "Parcial": f"${gastos_admin:,.2f}", "Total": ""},
                {"Concepto": "UTILIDAD DE OPERACIÓN", "Parcial": "", "Total": f"${utilidad_operacion:,.2f}"},
                {"Concepto": "  - Gastos financieros", "Parcial": f"${gastos_financieros:,.2f}", "Total": ""},
                {"Concepto": "UTILIDAD ANTES DE IMPUESTOS", "Parcial": "", "Total": f"${utilidad_antes_impuestos:,.2f}"},
                {"Concepto": "  - ISR (30%)", "Parcial": "", "Total": f"${isr_30:,.2f}"},
                {"Concepto": "  - IVA 16%", "Parcial": "", "Total": "$0.00"},
                {"Concepto": "UTILIDAD NETA (Después de impuestos)", "Parcial": "", "Total": f"${utilidad_neta:,.2f}"},
                {"Concepto": "RENTABILIDAD", "Parcial": "", "Total": f"{rentabilidad:.1f}%"}
            ]

            df_pnl = pd.DataFrame(pnl_data)

            # Tarjetas de KPI
            k1, k2, k3 = st.columns(3)
            k1.metric("Ventas Netas", f"${ventas_netas:,.2f}")
            k2.metric("Utilidad Neta", f"${utilidad_neta:,.2f}", delta=f"{rentabilidad:.1f}%")
            k3.metric("Rentabilidad", f"{rentabilidad:.1f}%")

            st.markdown(f"#### Estado de Resultados: **{titulo_periodo}**")
            st.dataframe(df_pnl, use_container_width=True, hide_index=True)

            # Historial filtrado por el mes seleccionado
            st.markdown(f"#### Detalle de transacciones de **{titulo_periodo}** ({len(df_filtrado)} movimientos)")
            cols_ver = ["fecha", "clasificacion", "servicio_producto", "proveedor", "subtotal", "iva", "total_neto", "metodo_pago", "banco_origen", "comentarios"]
            st.dataframe(df_filtrado[cols_ver], use_container_width=True, hide_index=True)

        else:
            st.info("No hay datos en la base de datos. Ejecuta el script SQL en Supabase para cargar el histórico.")
    except Exception as e:
        st.warning(f"Aviso en Estado de Resultados: {e}")
