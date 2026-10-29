import os
import base64
import tempfile
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
        
        # 3. Inicializar modelos
        self.modelo_texto = self._obtener_modelo_texto()
        self.modelo_vision = self._obtener_modelo_vision()

    def _obtener_modelo_texto(self):
        try:
            modelos_remotos = [m.id for m in self.client.models.list().data]
            prioridades = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"]
            for p in prioridades:
                if p in modelos_remotos: return p
            return "llama-3.3-70b-versatile"
        except Exception:
            return "llama-3.3-70b-versatile"

    def _obtener_modelo_vision(self):
        try:
            modelos_remotos = [m.id for m in self.client.models.list().data]
            prioridades_vision = ["llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"]
            for p in prioridades_vision:
                if p in modelos_remotos: return p
            return "llama-3.2-11b-vision-preview"
        except Exception:
            return "llama-3.2-11b-vision-preview"

    def _extraer_frame_video(self, video_bytes):
        try:
            import cv2
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp.write(video_bytes)
                tmp_path = tmp.name
            vid = cv2.VideoCapture(tmp_path)
            success, frame = vid.read()
            vid.release()
            os.remove(tmp_path)
            if success:
                _, buffer = cv2.imencode(".jpg", frame)
                return buffer.tobytes(), "image/jpeg"
        except Exception:
            pass
        return None, None

    def explicar_estructura_y_partes(self, texto_doc):
        prompt = f"Eres un tutor experto. Analiza este texto y genera una guía de estructura:\n{texto_doc[:5000]}"
        response = self.client.chat.completions.create(
            model=self.modelo_texto,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500
        )
        return response.choices[0].message.content

    def responder_pregunta(self, pregunta, contexto_estricto, contexto_referencial, contexto_alumno, historial, archivo_multimedia=None):
        # Truncado para evitar errores de tamaño
        msg_system = "Eres un tutor de ingeniería experto. Sé conciso. Prioriza siempre la NORMATIVA OBLIGATORIA."
        mensajes = [{"role": "system", "content": msg_system}]
        mensajes.append({"role": "user", "content": f"NORMATIVA: {contexto_estricto[:8000]}\nREF: {contexto_referencial[:3000]}\nTRABAJO: {contexto_alumno[:5000]}\n\nPREGUNTA: {pregunta}"})
        
        modelo = self.modelo_texto
        # Lógica de multimedia simplificada
        if archivo_multimedia and archivo_multimedia.get("tipo", "").startswith("image"):
            modelo = self.modelo_vision
            # ... lógica b64 ...
            
        response = self.client.chat.completions.create(
            model=modelo,
            messages=mensajes,
            temperature=0.2,
            max_tokens=800
        )
        return response.choices[0].message.content
