import os
import base64
import tempfile
import streamlit as st
from groq import Groq
from core.benchmark import CRITERIOS_REFERENCIA

class AsistenteDocumental:
    def __init__(self):
        api_key = st.secrets.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("No se encontró GROQ_API_KEY en secrets.")
        self.client = Groq(api_key=api_key)
        self.modelo_texto = self._obtener_modelo_texto()
        self.modelo_vision = self._obtener_modelo_vision()

    def _obtener_modelo_texto(self):
        """Selecciona el mejor modelo de texto disponible en Groq."""
        try:
            modelos_remotos = [m.id for m in self.client.models.list().data]
            modelos_texto = [m for m in modelos_remotos if "whisper" not in m.lower() and "guard" not in m.lower()]
            prioridades = [
                "llama-3.3-70b-versatile",
                "llama-3.1-70b-versatile",
                "llama-3.1-8b-instant",
                "qwen/qwen3.8-27b",
                "mixtral-8x7b-32768"
            ]
            for p in prioridades:
                if p in modelos_texto:
                    return p
            return modelos_texto[0] if modelos_texto else "llama-3.1-8b-instant"
        except Exception:
            return "llama-3.1-8b-instant"

    def _obtener_modelo_vision(self):
        """Selecciona un modelo multimodal en Groq capaz de ver imágenes."""
        try:
            modelos_remotos = [m.id for m in self.client.models.list().data]
            prioridades_vision = [
                "llama-3.2-11b-vision-preview",
                "llama-3.2-90b-vision-preview",
                "qwen/qwen3.8-27b"
            ]
            for p in prioridades_vision:
                if p in modelos_remotos:
                    return p
            vision_disponibles = [m for m in modelos_remotos if "vision" in m.lower()]
            if vision_disponibles:
                return vision_disponibles[0]
            return "llama-3.2-11b-vision-preview"
        except Exception:
            return "llama-3.2-11b-vision-preview"

    def _extraer_frame_video(self, video_bytes):
        """Extrae un fotograma del video si cv2 está instalado."""
        try:
            import cv2
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp.write(video_bytes)
                tmp_path = tmp.name
            
            vid = cv2.VideoCapture(tmp_path)
            success, frame = vid.read()
            vid.release()
            try:
                os.remove(tmp_path)
            except Exception:
                pass

            if success:
                _, buffer = cv2.imencode(".jpg", frame)
                return buffer.tobytes(), "image/jpeg"
        except Exception:
            pass
        return None, None

    def explicar_estructura_y_partes(self, texto_doc):
        prompt = f"""
        Eres un docente y tutor técnico experto.
        Analiza la normativa y bases suministradas y genera una GUÍA DE SU ESTRUCTURA:
        1. Objetivo y alcance principal.
        2. Desglose de capítulos y requisitos obligatorios (qué cálculos o datos requiere cada uno).
        3. Errores críticos que no se deben cometer.

        CONTENIDO:
        {texto_doc[:50000]}
        """
        response = self.client.chat.completions.create(
            model=self.modelo_texto,
            messages=[
                {"role": "system", "content": "Eres un tutor académico claro, exigente y didáctico."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content

    def responder_pregunta(self, pregunta, contexto_estricto, contexto_referencial, contexto_alumno, historial, archivo_multimedia=None):
        info_estricta = contexto_estricto if contexto_estricto else CRITERIOS_REFERENCIA
        info_referencial = contexto_referencial if contexto_referencial else "[No hay material referencial adicional cargado]"
        doc_info = f"\n--- BORRADOR ACTUAL DEL ALUMNO ---\n{contexto_alumno[:30000]}" if contexto_alumno else "\n[El alumno no ha subido borrador; consulta previa o de inicio]"

        mensajes = [
            {
                "role": "system",
                "content": (
                    "Eres un Profesor Tutor y Asesor Técnico experto en ingeniería y proyectos mineros.\n\n"
                    "DISPONES DE DOS FUENTES DE INFORMACIÓN CON DISTINTA JERARQUÍA:\n"
                    "1. NIVEL 1: 'NORMATIVA OBLIGATORIA (VERDAD ABSOLUTA)' -> Bases, rúbricas, fórmulas y límites legales oficiales. "
                    "Es inquebrantable. Si el alumno incumple algo de aquí, su entrega es NO APTA. Adviértele con firmeza técnica.\n"
                    "2. NIVEL 2: 'MATERIAL DE APOYO (REFERENCIAL)' -> Manuales, ejemplos y guías metodológicas. "
                    "Sirven para orientar el 'cómo hacer', pero NUNCA pueden contradecir a la Normativa Obligatoria.\n\n"
                    "REGLA DE CONFLICTO: Si un documento referencial sugiere algo que contradice a la Normativa Obligatoria, "
                    "manda 100% la Normativa Obligatoria sin excepción.\n"
                    "Sé muy claro diferenciando lo que es un 'REQUISITO EXIGIDO' de lo que es una 'SUGERENCIA RECOMENDADA'."
                )
            },
            {
                "role": "user",
                "content": (
                    f"=== [JERARQUÍA 1: NORMATIVA OBLIGATORIA (VERDAD ABSOLUTA)] ===\n{info_estricta[:30000]}\n\n"
                    f"=== [JERARQUÍA 2: MATERIAL DE APOYO (REFERENCIAL)] ===\n{info_referencial[:20000]}\n\n"
                    f"{doc_info}"
                )
            }
        ]

        # Sanitizar historial previo
        for msg in historial[-4:]:
            txt = msg.get("content", "")
            if isinstance(txt, str) and txt.strip():
                mensajes.append({"role": msg["role"], "content": txt})

        # Preparar mensaje multimodal o de texto
        modelo_elegido = self.modelo_texto

        if archivo_multimedia and archivo_multimedia.get("bytes"):
            tipo = archivo_multimedia.get("tipo", "")
            bytes_data = archivo_multimedia.get("bytes")
            nombre = archivo_multimedia.get("nombre", "archivo")

            if tipo.startswith("image"):
                b64_img = base64.b64encode(bytes_data).decode("utf-8")
                url_data = f"data:{tipo};base64,{b64_img}"
                mensajes.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": pregunta},
                        {"type": "image_url", "image_url": {"url": url_data}}
                    ]
                })
                modelo_elegido = self.modelo_vision

            elif tipo.startswith("video"):
                frame_bytes, frame_mime = self._extraer_frame_video(bytes_data)
                if frame_bytes:
                    b64_img = base64.b64encode(frame_bytes).decode("utf-8")
                    url_data = f"data:{frame_mime};base64,{b64_img}"
                    mensajes.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"{pregunta}\n[Fotograma extraído del video '{nombre}']:"},
                            {"type": "image_url", "image_url": {"url": url_data}}
                        ]
                    })
                    modelo_elegido = self.modelo_vision
                else:
                    mensajes.append({
                        "role": "user",
                        "content": f"{pregunta}\n[El alumno adjuntó el video '{nombre}'. Respóndele y recomiéndale una captura de pantalla si requiere precisión gráfica]."
                    })
        else:
            mensajes.append({"role": "user", "content": pregunta})

        response = self.client.chat.completions.create(
            model=modelo_elegido,
            messages=mensajes,
            temperature=0.2
        )
        return response.choices[0].message.content