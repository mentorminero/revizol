import os
import base64
import tempfile
import time
import streamlit as st
from groq import Groq, RateLimitError
from core.benchmark import CRITERIOS_REFERENCIA

class AsistenteDocumental:
    def __init__(self):
        api_key = st.secrets.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("No se encontró GROQ_API_KEY en secrets.")
        self.client = Groq(api_key=api_key)
        self.modelo_texto = self._obtener_modelo_texto()
        self.modelo_vision = self._obtener_modelo_vision()

    # ... (Mantén tus métodos _obtener_modelo_texto y _obtener_modelo_vision iguales) ...

    def _call_api_with_retry(self, **kwargs):
        """Intenta llamar a la API y si hay RateLimit, espera y reintenta."""
        max_retries = 3
        for i in range(max_retries):
            try:
                return self.client.chat.completions.create(**kwargs)
            except RateLimitError:
                if i < max_retries - 1:
                    wait = 2 ** i # Espera exponencial: 1s, 2s, 4s...
                    time.sleep(wait)
                    continue
                else:
                    raise
        return None

    def responder_pregunta(self, pregunta, contexto_estricto, contexto_referencial, contexto_alumno, historial, archivo_multimedia=None):
        # 1. Truncamos para no superar la ventana de contexto del modelo
        info_estricta = contexto_estricto[:12000]
        info_referencial = contexto_referencial[:8000]
        doc_info = contexto_alumno[:10000]

        mensajes = [
            {
                "role": "system",
                "content": (
                    "Eres un Profesor Tutor experto en minería. "
                    "Tu misión es dar feedback preciso y técnico. "
                    "REGLA: Si hay contradicción entre 'NORMATIVA OBLIGATORIA' y 'REFERENCIAL', manda la NORMATIVA. "
                    "Sé directo, usa bullet points y no excedas los 500 tokens de respuesta."
                )
            },
            {
                "role": "user",
                "content": f"NORMATIVA: {info_estricta}\n\nREFERENCIAS: {info_referencial}\n\nTRABAJO: {doc_info}\n\nPREGUNTA: {pregunta}"
            }
        ]
        
        # Sanitizar historial
        for msg in historial[-4:]:
            txt = msg.get("content", "")
            if isinstance(txt, str) and txt.strip():
                mensajes.append({"role": msg["role"], "content": txt})

        # Preparar mensaje
        modelo_elegido = self.modelo_texto
        # ... (Mantén tu lógica de adjuntos igual, solo cambia la llamada final a la API)

        # 2. LLAMADA PROTEGIDA CON RETRY Y LÍMITE DE TOKENS
        response = self._call_api_with_retry(
            model=modelo_elegido,
            messages=mensajes,
            temperature=0.2,
            max_tokens=1000 # <-- LIMITADOR CLAVE PARA EL ERROR 429
        )
        return response.choices[0].message.content
