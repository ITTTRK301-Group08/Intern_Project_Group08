from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.auth import ApiResponse


class CVResponse(BaseModel):
    id: int
    file_name: str
    file_size: int
    mime_type: str
    extracted_text: str | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CVUploadData(BaseModel):
    cv: CVResponse


CVUploadResponse = ApiResponse[CVUploadData]
