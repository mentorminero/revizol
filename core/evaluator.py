import json
import streamlit as st
from groq import Groq
from pydantic import BaseModel, Field
from typing import List

# Modelos estructurados para la auditoría
class ItemChecklist(BaseModel):
    requisito: str
    estado: str = Field(description="CUMPLE, NO_CUMPLE o PARCIAL")
    severidad: str = Field(description="CRITICA, ALTA, MEDIA o BAJA")
    pagina_hallazgo: str = Field(description="Número de página donde se encontró o 'No encontrada'")
    evidencia_o_falta: str

class ObservacionCalidad(BaseModel):
    categoria: str
    pagina: str
    descripcion: str
    sugerencia_mejora: str

class ReporteAuditoria(BaseModel):
    porcentaje_completitud: int = Field(description="Porcentaje de 0 a 100 de cumplimiento de las bases estrictas")
    calidad_general: str = Field(description="SOBRESALIENTE, SATISFACTORIO, OBSERVADO o DEFICIENTE")
    resumen_ejecutivo: str
    checklist_requisitos: List[ItemChecklist]
    observaciones_calidad: List[ObservacionCalidad]

class EvaluadorDocumental:
    def __init__(self):
        api_key = st.secrets.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("No se encontró GROQ_API_KEY en secrets.")
        self.client = Groq(api_key=api_key)
        self.modelo = "qwen/qwen3.8-27b"

    def auditar_documento(self, contexto_estricto, contexto_referencial, paginas_alumno):
        texto_alumno_completo = "\n".join([f"[Pág. {p['pagina']}]: {p['contenido']}" for p in paginas_alumno])

        prompt_sistema = """
        Eres un Auditor Académico y Evaluador de Proyectos de Ingeniería.
        Tu trabajo es auditar minuciosamente el trabajo del alumno comparándolo contra dos fuentes de información:

        1. REQUISITOS ESTRICTOS (VERDAD ABSOLUTA): Bases oficiales, rúbricas obligatorias y parámetros inquebrantables.
           - El porcentaje de completitud y los ítems del 'checklist_requisitos' dependen EXCLUSIVAMENTE de este nivel.
           - Si algo falta o no cumple aquí, su estado debe ser NO_CUMPLE o PARCIAL con severidad ALTA o CRÍTICA.

        2. GUÍAS Y REFERENCIAS (RECOMENDACIONES): Manuales, ejemplos o metodologías sugeridas.
           - Las discrepancias con este material NO bajan la completitud, sino que se reportan en 'observaciones_calidad' como sugerencias de optimización.

        Responde OBLIGATORIAMENTE en formato JSON estructurado que coincida con este esquema:
        {
            "porcentaje_completitud": int,
            "calidad_general": "SOBRESALIENTE" | "SATISFACTORIO" | "OBSERVADO" | "DEFICIENTE",
            "resumen_ejecutivo": "texto",
            "checklist_requisitos": [
                {
                    "requisito": "texto",
                    "estado": "CUMPLE" | "NO_CUMPLE" | "PARCIAL",
                    "severidad": "CRITICA" | "ALTA" | "MEDIA" | "BAJA",
                    "pagina_hallazgo": "Pág. X o No encontrada",
                    "evidencia_o_falta": "texto"
                }
            ],
            "observaciones_calidad": [
                {
                    "categoria": "Metodología / Formato / Cálculos",
                    "pagina": "Pág. X",
                    "descripcion": "texto",
                    "sugerencia_mejora": "texto"
                }
            ]
        }
        """

        prompt_usuario = f"""
        === BASES ESTRICTAS OBLIGATORIAS (VERDAD ABSOLUTA) ===
        {contexto_estricto[:35000]}

        === MATERIAL DE APOYO Y REFERENCIAS (SUGERIDO) ===
        {contexto_referencial[:20000]}

        === DOCUMENTO DEL ALUMNO A AUDITAR ===
        {texto_alumno_completo[:50000]}
        """

        response = self.client.chat.completions.create(
            model=self.modelo,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        datos_json = json.loads(response.choices[0].message.content)
        return ReporteAuditoria(**datos_json)
