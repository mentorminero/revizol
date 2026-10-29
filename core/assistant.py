import os
import time
import streamlit as st
from groq import Groq, RateLimitError
from core.benchmark import CRITERIOS_REFERENCIA

class AsistenteDocumental:
    def __init__(self):
        # 1. Asegurar que la API KEY esté presente
        api_key = st.secrets.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("No se encontró GROQ_API_KEY en secrets.")
            
        # 2. Inicializar cliente
        self.client = Groq(api_key=api_key)
        
        # Modelo oficial confirmado y ultra-rápido en tu cuenta
        self.modelo = "qwen/qwen3.8-27b"

    def _call_api_with_retry(self, **kwargs):
        """Sistema de reintento automático (Backoff) si Groq satura por Rate Limit (429)"""
        max_retries = 3
        for i in range(max_retries):
            try:
                return self.client.chat.completions.create(**kwargs)
            except RateLimitError:
                if i < max_retries - 1:
                    time.sleep(2 ** i) # Espera 1s, 2s, 4s y reintenta
                    continue
                else:
                    raise
        return None

    def explicar_estructura_y_partes(self, texto_doc):
        prompt = f"""
        Eres un docente y tutor técnico experto en ingeniería y proyectos mineros.
        Analiza las bases suministradas y genera una GUÍA DE SU ESTRUCTURA:
        1. Objetivo y alcance principal.
        2. Desglose de capítulos y requisitos obligatorios.
        3. Errores críticos que no se deben cometer.

        CONTENIDO:
        {texto_doc[:12000]}
        """
        response = self._call_api_with_retry(
            model=self.modelo,
            messages=[
                {"role": "system", "content": "Eres un tutor académico claro, exigente y didáctico."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=800
        )
        return response.choices[0].message.content

    def responder_pregunta(self, pregunta, contexto_estricto, contexto_referencial, contexto_alumno, historial, archivo_multimedia=None):
        # Truncados inteligentes para proteger los tokens de entrada
        info_estricta = contexto_estricto[:10000]
        info_referencial = contexto_referencial[:5000]
        doc_info = f"\n--- BORRADOR DEL ALUMNO ---\n{contexto_alumno[:8000]}" if contexto_alumno else "\n[El alumno aún no ha subido su borrador]"

        mensajes = [
            {
                "role": "system",
                "content": (
                    "Eres un Profesor Tutor y Asesor Técnico experto en ingeniería y proyectos mineros.\n\n"
                    "DISPONES DE DOS FUENTES DE INFORMACIÓN CON DISTINTA JERARQUÍA:\n"
                    "1. NORMATIVA OBLIGATORIA (VERDAD ABSOLUTA): Bases, rúbricas, fórmulas y límites legales oficiales. "
                    "Es inquebrantable. Si el alumno incumple algo de aquí, adviértele con firmeza técnica.\n"
                    "2. MATERIAL DE APOYO (REFERENCIAL): Manuales y guías metodológicas.\n\n"
                    "REGLA DE CONFLICTO: Si un documento referencial contradice a la Normativa Obligatoria, "
                    "manda 100% la Normativa Obligatoria sin excepción.\n"
                    "Sé conciso, directo, técnico y responde en máximo 3 párrafos o viñetas."
                )
            },
            {
                "role": "user",
                "content": (
                    f"=== [NORMATIVA OBLIGATORIA] ===\n{info_estricta}\n\n"
                    f"=== [MATERIAL DE APOYO] ===\n{info_referencial}\n\n"
                    f"{doc_info}"
                )
            }
        ]

        # Sanitizar historial (últimas 2 interacciones para ahorrar tokens)
        for msg in historial[-4:]:
            txt = msg.get("content", "")
            if isinstance(txt, str) and txt.strip():
                mensajes.append({"role": msg["role"], "content": txt})

        # Manejo de multimedia adaptado al modelo de texto
        if archivo_multimedia and archivo_multimedia.get("bytes"):
            nombre = archivo_multimedia.get("nombre", "archivo")
            pregunta = f"{pregunta} [Nota del sistema: El usuario adjuntó el archivo multimedia '{nombre}']."

        mensajes.append({"role": "user", "content": pregunta})

        # Llamada protegida contra Rate Limits
        response = self._call_api_with_retry(
            model=self.modelo,
            messages=mensajes,
            temperature=0.2,
            max_tokens=800
        )
        return response.choices[0].message.content
