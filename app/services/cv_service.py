import logging
import re
import uuid
from pathlib import Path

import pymupdf as fitz  # PyMuPDF
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.cv import CV

logger = logging.getLogger(__name__)

MAX_CV_SIZE_BYTES = 5 * 1024 * 1024
PDF_MAGIC_BYTES = b"%PDF-"
ALLOWED_MIME_TYPES = {"application/pdf"}
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "cvs"


def _safe_display_name(filename: str | None) -> str:
    if not filename:
        return "upload.pdf"
    name = Path(filename).name
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name or "upload.pdf"


def validate_pdf(upload: UploadFile, content: bytes) -> str:
    filename = _safe_display_name(upload.filename)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed")

    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")

    if len(content) > MAX_CV_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size exceeds 5MB limit")

    if upload.content_type and upload.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file MIME type")

    if not content.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PDF file content")

    return filename


def save_cv_file(content: bytes) -> tuple[Path, str]:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    stored_file_name = f"{uuid.uuid4()}.pdf"
    target = (UPLOAD_ROOT / stored_file_name).resolve()
    root_resolved = UPLOAD_ROOT.resolve()
    if root_resolved not in target.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path")
    if target.exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store file")
    target.write_bytes(content)
    return target, stored_file_name


def extract_pdf_text(file_path: Path) -> str:
    doc = None
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            try:
                if not doc.authenticate(""):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Encrypted PDF is not supported",
                    )
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Encrypted PDF is not supported",
                ) from exc
        parts: list[str] = []
        for page in doc:
            parts.append(page.get_text("text") or "")
        text = "\n".join(parts)
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text
    except HTTPException:
        raise
    except Exception as exc:
        logger.info("PDF text extraction failed")  # no content logged
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read or extract text from PDF",
        ) from exc
    finally:
        if doc is not None:
            doc.close()


def upload_cv(db: Session, user_id: int, upload: UploadFile) -> tuple[CV, bool]:
    try:
        content = upload.file.read()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to read uploaded file") from exc

    original_name = validate_pdf(upload, content)
    file_path, _stored_name = save_cv_file(content)

    try:
        extracted_text = extract_pdf_text(file_path)
        has_meaningful_text = bool(extracted_text and re.search(r"\S", extracted_text))
        cv = CV(
            user_id=user_id,
            file_name=original_name,
            file_path=str(file_path),
            mime_type="application/pdf",
            file_size=len(content),
            extracted_text=extracted_text if has_meaningful_text else "",
            is_active=True,
        )
        db.add(cv)
        db.commit()
        db.refresh(cv)
        return cv, has_meaningful_text
    except HTTPException:
        db.rollback()
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            logger.warning("Failed to clean up uploaded file")
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            logger.warning("Failed to clean up uploaded file after DB error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error") from exc
    except Exception as exc:
        db.rollback()
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            logger.warning("Failed to clean up uploaded file after unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Upload processing failed") from exc
