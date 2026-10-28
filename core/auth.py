import streamlit as st

def recargar_pagina():
    """Compatible tanto con versiones antiguas como modernas de Streamlit"""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

def verificar_acceso(correo, clave):
    correo_limpio = correo.strip().lower()
    clave_maestra = st.secrets.get("CLAVE_CURSO", "Clase2025")
    lista_alumnos = [c.lower() for c in st.secrets.get("ALUMNOS_AUTORIZADOS", [])]

    if not correo_limpio:
        return False, "Ingresa tu correo institucional."
    if correo_limpio not in lista_alumnos:
        return False, "⛔ Tu correo no está en la lista de alumnos autorizados."
    if clave != clave_maestra:
        return False, "🔒 Contraseña de clase incorrecta."

    return True, "Acceso concedido."

def login_interfaz():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
        st.session_state["usuario_actual"] = None

    if not st.session_state["autenticado"]:
        _, col2, _ = st.columns([1, 2, 1])
        with col2:
            st.title("🎓 Portal de Auditoría")
            st.caption("Acceso exclusivo para alumnos de la asignatura.")
            with st.form("form_login"):
                correo = st.text_input("Correo Institucional", placeholder="estudiante@universidad.edu")
                clave = st.text_input("Contraseña de Clase", type="password")
                btn = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
                if btn:
                    es_valido, msj = verificar_acceso(correo, clave)
                    if es_valido:
                        st.session_state["autenticado"] = True
                        st.session_state["usuario_actual"] = correo.strip().lower()
                        st.success(msj)
                        recargar_pagina()
                    else:
                        st.error(msj)
        return False
    return True

def boton_cerrar_sesion():
    if st.session_state.get("autenticado"):
        st.sidebar.markdown(f"👤 **Alumno:** `{st.session_state['usuario_actual']}`")
        if st.sidebar.button("🚪 Cerrar Sesión"):
            st.session_state.clear()
            recargar_pagina()