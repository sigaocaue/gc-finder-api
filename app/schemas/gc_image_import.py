"""Schemas para importação de GC por imagem (extração OCR e salvamento)."""

from pydantic import BaseModel, Field


# --- Tipos compartilhados entre extração e salvamento ---


class LeaderContactExtracted(BaseModel):
    """Contato extraído de um líder."""

    type: str = "whatsapp"
    value: str
    label: str | None = None


class LeaderExtracted(BaseModel):
    """Líder extraído da imagem."""

    name: str
    contacts: list[LeaderContactExtracted] = []


class MeetingExtracted(BaseModel):
    """Encontro extraído da imagem."""

    # 0=Dom, 1=Seg, 2=Ter, 3=Qua, 4=Qui, 5=Sex, 6=Sáb
    weekday: int = Field(..., ge=0, le=6)
    start_time: str
    notes: str | None = None


class GcExtractedData(BaseModel):
    """Dados completos de um GC extraídos da imagem."""

    name: str
    description: str | None = None
    zip_code: str | None = None
    street: str
    number: str | None = None
    complement: str | None = None
    neighborhood: str | None = None
    city: str = "Jundiaí"
    state: str = "SP"
    latitude: float | None = None
    longitude: float | None = None
    leaders: list[LeaderExtracted] = []
    meetings: list[MeetingExtracted] = []


# --- POST /image → 202 ---


class GcImportStartResponse(BaseModel):
    """Resposta ao iniciar extração de imagem."""

    job_id: str
    status: str
    stream_url: str


# --- Evento SSE (GET /jobs/{job_id}/stream) ---


class GcJobStatusEvent(BaseModel):
    """Evento de status do job de extração."""

    status: str
    progress: str | None = None
    result: list[GcExtractedData] | None = None
    error: str | None = None

    def to_sse(self, event: str = "status") -> str:
        """Serializa o evento no formato SSE."""
        import json

        json_data = json.dumps(
            self.model_dump(exclude_none=True), ensure_ascii=False
        )
        return f"event: {event}\ndata: {json_data}\n\n"


class GcHeartbeatEvent(BaseModel):
    """Evento de heartbeat SSE."""

    ts: str

    def to_sse(self) -> str:
        """Serializa o heartbeat no formato SSE."""
        import json

        json_data = json.dumps(self.model_dump(), ensure_ascii=False)
        return f"event: heartbeat\ndata: {json_data}\n\n"


# --- POST /save ---


class GcImportSaveRequest(BaseModel):
    """Dados para salvar um GC importado no banco de dados."""

    name: str
    description: str | None = None
    zip_code: str | None = None
    street: str
    number: str | None = None
    complement: str | None = None
    neighborhood: str | None = None
    city: str = "Jundiaí"
    state: str = "SP"
    latitude: float | None = None
    longitude: float | None = None
    leaders: list[LeaderExtracted] = []
    meetings: list[MeetingExtracted] = []
