import os
import glob
import streamlit as st
import pandas as pd
from core.auth import login_interfaz, boton_cerrar_sesion
from core.extractor import extraer_texto_pdf
from core.assistant import AsistenteDocumental
from core.evaluator import EvaluadorDocumental
from core.calculator import calcular_ley_corte, evaluar_caso_base, correr_montecarlo

st.set_page_config(
    page_title="Tutor y Auditoría Documental",
    layout="wide",
    page_icon="🎓"
)

# Ocultar footer "Made with Streamlit" y menú superior
st.markdown("""
    <style>
    footer {visibility: hidden; display: none !important;}
    #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# 1. Control de Acceso por Correo
if not login_interfaz():
    st.stop()

boton_cerrar_sesion()

# 2. Inicialización de Estados de Sesión
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "texto_estricta" not in st.session_state:
    st.session_state["texto_estricta"] = ""
if "docs_estricta" not in st.session_state:
    st.session_state["docs_estricta"] = []
if "texto_referencial" not in st.session_state:
    st.session_state["texto_referencial"] = ""
if "docs_referencial" not in st.session_state:
    st.session_state["docs_referencial"] = []
if "texto_doc_completo" not in st.session_state:
    st.session_state["texto_doc_completo"] = ""
if "paginas_doc" not in st.session_state:
    st.session_state["paginas_doc"] = None
if "media_key" not in st.session_state:
    st.session_state["media_key"] = 0

asistente = AsistenteDocumental()
evaluador = EvaluadorDocumental()

# ==============================================================================
# 3. CARGA AUTOMÁTICA EN BACKGROUND (2 CARPETAS)
# ==============================================================================
CARPETA_ESTRICTA = os.path.join("data", "estricta")
CARPETA_REFERENCIAL = os.path.join("data", "referencial")

os.makedirs(CARPETA_ESTRICTA, exist_ok=True)
os.makedirs(CARPETA_REFERENCIAL, exist_ok=True)

def cargar_documentos_desde_carpeta(carpeta_origen, etiqueta):
    textos, nombres = [], []
    rutas = glob.glob(os.path.join(carpeta_origen, "*.*"))
    for ruta in sorted(rutas):
        nombre_arch = os.path.basename(ruta)
        ext = nombre_arch.lower().split(".")[-1]
        try:
            if ext == "pdf":
                with open(ruta, "rb") as f:
                    paginas = extraer_texto_pdf(f.read())
                    textos.append(f"=== [{etiqueta}]: {nombre_arch} ===\n" + "\n".join([p["contenido"] for p in paginas]))
                    nombres.append(nombre_arch)
            elif ext in ["txt", "md"]:
                with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
                    textos.append(f"=== [{etiqueta}]: {nombre_arch} ===\n{f.read()}")
                    nombres.append(nombre_arch)
        except Exception as e:
            st.sidebar.error(f"Error leyendo '{nombre_arch}': {e}")
    return "\n\n".join(textos), nombres

if not st.session_state["texto_estricta"]:
    t_est, n_est = cargar_documentos_desde_carpeta(CARPETA_ESTRICTA, "NORMATIVA OBLIGATORIA (VERDAD ABSOLUTA)")
    st.session_state["texto_estricta"] = t_est
    st.session_state["docs_estricta"] = n_est

if not st.session_state["texto_referencial"]:
    t_ref, n_ref = cargar_documentos_desde_carpeta(CARPETA_REFERENCIAL, "MATERIAL DE APOYO (REFERENCIA)")
    st.session_state["texto_referencial"] = t_ref
    st.session_state["docs_referencial"] = n_ref

# ==============================================================================
# 4. MENÚ LATERAL
# ==============================================================================
with st.sidebar:
    st.header("📂 Documentación de Soporte")

    total_est = len(st.session_state["docs_estricta"])
    with st.expander(f"🔴 Verdad Absoluta / Estricta ({total_est})", expanded=False):
        for doc in st.session_state["docs_estricta"]:
            st.markdown(f"- 🔒 `{doc}`")

    total_ref = len(st.session_state["docs_referencial"])
    with st.expander(f"🟡 Guías y Referencias ({total_ref})", expanded=False):
        for doc in st.session_state["docs_referencial"]:
            st.markdown(f"- 📖 `{doc}`")

    st.markdown("---")
    st.subheader("Tu Trabajo / Entrega")
    doc_upload = st.file_uploader("Subir tu Borrador para Auditar (PDF):", type=["pdf"], key="doc_uploader")

    if doc_upload and st.session_state.get("doc_actual") != doc_upload.name:
        with st.spinner("Procesando documento..."):
            paginas_d = extraer_texto_pdf(doc_upload.read())
            st.session_state["paginas_doc"] = paginas_d
            st.session_state["texto_doc_completo"] = "\n".join([f"[Pág. {p['pagina']}]: {p['contenido']}" for p in paginas_d])
            st.session_state["doc_actual"] = doc_upload.name
            st.session_state.pop("reporte_generado", None)
        st.success("¡Documento cargado!")

# ==============================================================================
# 5. PESTAÑAS PRINCIPALES DE LA PLATAFORMA (3 PESTAÑAS)
# ==============================================================================
tab_chat, tab_auditoria, tab_calculos = st.tabs([
    "💬 Chat de Consultas y Tutoría", 
    "⚖️ Auditoría y Comparación",
    "🧮 Simulador y Cálculos Mineros"
])

# ------------------------------------------------------------------------------
# PESTAÑA 1: CHAT TUTOR
# ------------------------------------------------------------------------------
with tab_chat:
    st.subheader("🤖 Consultas sobre las Bases, Metodología y Cálculos")
    
    if st.session_state["texto_estricta"] or st.session_state["texto_doc_completo"]:
        if st.button("📖 Desglosar Requisitos Clave Obligatorios"):
            texto_a_explicar = st.session_state["texto_doc_completo"] or st.session_state["texto_estricta"]
            with st.spinner("Generando desglose..."):
                explicacion = asistente.explicar_estructura_y_partes(texto_a_explicar)
                st.markdown(explicacion)

    st.markdown("---")

    for msg in st.session_state["chat_history"]:
        if hasattr(st, "chat_message"):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("media"):
                    m = msg["media"]
                    if m["tipo"].startswith("image"):
                        st.image(m["bytes"], caption=m.get("nombre", ""), width=380)
                    elif m["tipo"].startswith("video"):
                        st.video(m["bytes"])
        else:
            if msg["role"] == "user":
                st.markdown(f"**🧑‍🎓 Tú:** {msg['content']}")
            else:
                st.markdown(f"**🤖 Tutor:** {msg['content']}")

    with st.expander("📎 Adjuntar captura, foto o video a tu consulta (opcional)", expanded=False):
        media_upload = st.file_uploader(
            "Selecciona una imagen o video:",
            type=["png", "jpg", "jpeg", "webp", "mp4", "mov"],
            key=f"chat_media_{st.session_state['media_key']}"
        )

    query = None
    archivo_adjunto = None

    if hasattr(st, "chat_input"):
        input_text = st.chat_input("Escribe tu duda aquí...")
        if input_text:
            query = input_text.strip()
            if media_upload:
                archivo_adjunto = {"nombre": media_upload.name, "tipo": media_upload.type, "bytes": media_upload.getvalue()}
    else:
        with st.form("form_chat", clear_on_submit=True):
            col_in, col_btn = st.columns([5, 1])
            with col_in:
                texto_ingresado = st.text_input("Consulta:", placeholder="Escribe tu duda aquí...", label_visibility="collapsed")
            with col_btn:
                enviar = st.form_submit_button("Enviar", use_container_width=True)
            if enviar:
                if texto_ingresado.strip():
                    query = texto_ingresado.strip()
                elif media_upload:
                    query = f"Consulta sobre el archivo adjunto: {media_upload.name}"
                if media_upload:
                    archivo_adjunto = {"nombre": media_upload.name, "tipo": media_upload.type, "bytes": media_upload.getvalue()}

    if query:
        msg_usuario = {"role": "user", "content": query}
        if archivo_adjunto:
            msg_usuario["media"] = archivo_adjunto
            st.session_state["media_key"] += 1
        st.session_state["chat_history"].append(msg_usuario)
        
        with st.spinner("El tutor está analizando las bases..."):
            resp = asistente.responder_pregunta(
                pregunta=query,
                contexto_estricto=st.session_state["texto_estricta"],
                contexto_referencial=st.session_state["texto_referencial"],
                contexto_alumno=st.session_state["texto_doc_completo"],
                historial=st.session_state["chat_history"],
                archivo_multimedia=archivo_adjunto
            )
            st.session_state["chat_history"].append({"role": "assistant", "content": resp})
            st.rerun()

# ------------------------------------------------------------------------------
# PESTAÑA 2: AUDITORÍA
# ------------------------------------------------------------------------------
with tab_auditoria:
    st.subheader("⚖️ Dictamen de Cumplimiento y Calidad")
    if not st.session_state["paginas_doc"]:
        st.warning("⚠️ Sube tu documento PDF en la barra lateral para auditar.")
    elif not st.session_state["texto_estricta"]:
        st.error("⚠️ No se encontraron documentos obligatorios en 'data/estricta/'.")
    else:
        if st.button("🚀 Iniciar Auditoría Completa", type="primary"):
            with st.spinner("Auditando tu trabajo..."):
                reporte = evaluador.auditar_documento(
                    contexto_estricto=st.session_state["texto_estricta"],
                    contexto_referencial=st.session_state["texto_referencial"],
                    paginas_alumno=st.session_state["paginas_doc"]
                )
                st.session_state["reporte_generado"] = reporte

        if "reporte_generado" in st.session_state:
            rep = st.session_state["reporte_generado"]
            c1, c2 = st.columns(2)
            c1.metric("Cumplimiento Normativo", f"{rep.porcentaje_completitud}%")
            c2.metric("Calidad Metodológica", rep.calidad_general)
            st.info(f"**Dictamen Oficial:** {rep.resumen_ejecutivo}")

            for item in rep.checklist_requisitos:
                icono = "✅" if item.estado == "CUMPLE" else ("❌" if item.estado == "NO_CUMPLE" else "⚠️")
                with st.expander(f"{icono} [{item.estado}] {item.requisito} — Severidad: {item.severidad}"):
                    st.write(f"**Página:** {item.pagina_hallazgo}")
                    st.write(f"**Dictamen:** {item.evidencia_o_falta}")

# ------------------------------------------------------------------------------
# PESTAÑA 3: SIMULADOR Y CÁLCULOS MINEROS EN VIVO (Fórmulas Python)
# ------------------------------------------------------------------------------
with tab_calculos:
    st.subheader("🧮 Motor Matemático y Simulación de Riesgo (Montecarlo)")
    st.caption("Cálculos ejecutados en Python con el régimen tributario minero peruano (Ley 29788, PTU 8% e IR 29.5%).")

    # Módulo A: Calculadora de Ley de Corte
    with st.expander("📌 1. Calculadora de Ley de Corte Marginal (Cut-off Grade)", expanded=True):
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            cp_input = st.number_input("Costo Proceso ($/t):", value=12.00, step=0.50)
            ga_input = st.number_input("Costo G&A ($/t):", value=1.50, step=0.10)
        with col_c2:
            pcu_input = st.number_input("Precio Cu ($/t):", value=12000.0, step=500.0)
            gv_input = st.number_input("Costo Venta GV ($/t):", value=650.0, step=50.0)
        with col_c3:
            rec_input = st.slider("Recuperación Metalúrgica (%):", 70.0, 98.0, 90.0)
            
        cog_result = calcular_ley_corte(cp_input, ga_input, pcu_input, gv_input, rec_input)
        st.metric("Ley de Corte Crítica (Cut-Off)", f"{cog_result:.3f} % Cu")

    st.markdown("---")

    # Módulo B: Evaluación Económica y Montecarlo
    st.markdown("### 📊 2. Evaluación Económica y Análisis de Riesgo")
    
    # Cargar cronograma consolidado
    archivo_lom = 'Cronograma_Consolidado_LOM.xlsx'
    if not os.path.exists(archivo_lom):
        st.warning(f"⚠️ Para correr la evaluación económica se necesita el archivo '{archivo_lom}' en la raíz del proyecto.")
    else:
        df_lom_carga = pd.read_excel(archivo_lom)
        
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            capex_m_sim = st.number_input("CAPEX Inicial (Millones USD):", value=650.0, step=25.0)
            precio_sim = st.number_input("Precio Cobre Base (USD/t):", value=12000.0, step=500.0)
        with col_p2:
            mina_sim = st.number_input("Costo Minado ($/t):", value=2.70, step=0.10)
            planta_sim = st.number_input("Costo Proceso ($/t):", value=12.00, step=0.50)
        with col_p3:
            rec_sim = st.slider("Recuperación Cu (%):", 75.0, 98.0, 90.0, key="rec_sim_mc")
            tasa_sim = st.number_input("Tasa Descuento WACC (%):", value=10.0, step=0.5)

        # Botón para correr Caso Base determinístico
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            ejecutar_base = st.button("📈 Evaluar Flujo de Caja Caso Base (Post-Tax)", use_container_width=True)
        with c_btn2:
            ejecutar_mc = st.button("🎲 Ejecutar Montecarlo (10,000 Simulaciones)", type="primary", use_container_width=True)

        if ejecutar_base:
            with st.spinner("Calculando depreciación acelerada e impuestos..."):
                res_base = evaluar_caso_base(df_lom_carga, capex_m_sim, precio_sim, mina_sim, planta_sim, rec_sim, tasa_sim)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("VAN Neto del Proyecto", f"{res_base['VAN_M']:,.2f} M USD")
                m2.metric("TIR Post-Tax", f"{res_base['TIR']:.2f} %")
                m3.metric("Payback Descontado", f"{res_base['PRD']:.2f} Años")
                
                st.markdown("#### Flujo de Caja Detallado Anual (en Millones de USD):")
                st.dataframe(res_base['tabla'], use_container_width=True)

        if ejecutar_mc:
            with st.spinner("Corriendo 10,000 iteraciones con distribuciones de riesgo..."):
                res_mc = correr_montecarlo(df_lom_carga, capex_m_sim, precio_sim, mina_sim, planta_sim, rec_sim, tasa_sim, n_sim=10000)
                
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("P10 Pesimista", f"{res_mc['P10']:,.1f} M USD")
                k2.metric("P50 Mediana", f"{res_mc['P50']:,.1f} M USD")
                k3.metric("P90 Optimista", f"{res_mc['P90']:,.1f} M USD")
                k4.metric("Probabilidad VAN > 0", f"{res_mc['prob_exito']:.1f} %")
                
                st.pyplot(res_mc['figura'])