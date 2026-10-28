from pydantic import BaseModel, Field
from typing import List

class ItemEvaluacion(BaseModel):
    requisito: str = Field(description="Nombre o título del requisito evaluado")
    estado: str = Field(description="Estado del cumplimiento: CUMPLE, NO_CUMPLE o PARCIAL")
    pagina_hallazgo: str = Field(description="Páginas donde se localiza o 'No presente'")
    evidencia_o_falta: str = Field(description="Explicación concreta de qué cumple o qué falta")
    severidad: str = Field(description="Severidad: CRITICO, IMPORTANTE o MENOR")

class ObservacionCalidad(BaseModel):
    categoria: str = Field(description="Categoría: CONTRADICCION, AMBIGUEDAD, CALIDAD_TECNICA o REDACCION")
    descripcion: str = Field(description="Detalle del hallazgo")
    pagina: str = Field(description="Página donde ocurre el hallazgo")
    sugerencia_mejora: str = Field(description="Sugerencia de corrección")

class ReporteAuditoria(BaseModel):
    resumen_ejecutivo: str = Field(description="Resumen ejecutivo del estado del documento")
    porcentaje_completitud: int = Field(ge=0, le=100, description="Porcentaje de completitud de 0 a 100")
    calidad_general: str = Field(description="Calidad general: EXCELENTE, BUENA, DEFICIENTE o CRITICA")
    checklist_requisitos: List[ItemEvaluacion]
    observaciones_calidad: List[ObservacionCalidad]