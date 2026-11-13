import logging
import re
import uuid
from pathlib import Path

import pymupdf as fitz  # PyMuPDF
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.cv import CV
from app.schemas.cv import CVDeleteData, CVExtractionWarning, CVResponse

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


def assess_extracted_text(extracted_text: str | None) -> tuple[bool, str]:
    cleaned = (extracted_text or "").strip()
    if not cleaned:
        return False, "empty"
    alnum_count = len(re.findall(r"[0-9A-Za-zÀ-ỹ]", cleaned))
    word_count = len(re.findall(r"\S+", cleaned))
    if alnum_count < 10 or word_count < 2:
        return False, "too_short"
    return True, "ok"


def inspect_pdf_images(file_path: Path) -> bool:
    doc = None
    try:
        if not file_path.exists():
            return False
        doc = fitz.open(file_path)
        return any(bool(page.get_images()) for page in doc)
    except Exception:
        return False
    finally:
        if doc is not None:
            doc.close()


def build_cv_extraction_warning(
    cv: CV, *, is_scanned_pdf: bool | None = None
) -> CVExtractionWarning | None:
    has_text, extraction_status = assess_extracted_text(cv.extracted_text)
    if has_text:
        return None

    if is_scanned_pdf is None and cv.file_path:
        is_scanned_pdf = inspect_pdf_images(Path(cv.file_path))

    if is_scanned_pdf:
        cause = (
            "CV PDF nay la anh quet (chi chua hinh anh, khong co lop van ban) "
            "nen he thong khong the trich xuat noi dung chu."
        )
    elif extraction_status == "too_short":
        cause = (
            "Noi dung van ban trich xuat tu CV PDF qua ngan hoac khong du thong tin "
            "(co the la PDF anh quet mot phan hoac chi chua ky tu trang tri)."
        )
    else:
        cause = (
            "Khong trich xuat duoc noi dung van ban tu file PDF "
            "(co the la file anh quet khong co lop van ban)."
        )

    return CVExtractionWarning(
        code="PDF_NO_EXTRACTABLE_TEXT",
        cause=cause,
        guidance=(
            "Vui long tai len file CV PDF co lop van ban (xuat tu Word/Google Docs), "
            "hoac cap nhat Ho so ca nhan de chuyen sang phan tich tu du lieu ho so khai bao."
        ),
        recommended_actions=[
            "Cap nhat Ho so ca nhan (/profile) voi diem manh, ky nang tu danh gia va gioi thieu ban than.",
            "Chuyen sang trang Phan tich (/analysis?source=profile) de phan tich truc tiep tu du lieu ho so.",
            "Hoac xuat lai CV sang PDF co lop van ban va tai len lai.",
        ],
        profile_url="/profile",
        analysis_url="/analysis?source=profile",
    )


def serialize_cv_response(cv: CV, *, analysis_count: int = 0) -> CVResponse:
    has_text, extraction_status = assess_extracted_text(cv.extracted_text)
    return CVResponse(
        id=cv.id,
        file_name=cv.file_name,
        file_size=cv.file_size,
        mime_type=cv.mime_type,
        extracted_text=cv.extracted_text,
        is_active=cv.is_active,
        created_at=cv.created_at,
        has_text=has_text,
        extraction_status=extraction_status if has_text else "no_text",
        has_analysis=analysis_count > 0,
        analysis_count=analysis_count,
    )


def upload_cv(db: Session, user_id: int, upload: UploadFile) -> tuple[CV, bool]:
    try:
        content = upload.file.read()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to read uploaded file") from exc

    original_name = validate_pdf(upload, content)
    file_path, _stored_name = save_cv_file(content)

    try:
        extracted_text = extract_pdf_text(file_path)
        has_meaningful_text, _ = assess_extracted_text(extracted_text)
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


def list_user_cvs(
    db: Session, user_id: int, *, include_inactive: bool = False
) -> list[CVResponse]:
    query = select(CV).where(CV.user_id == user_id)
    if not include_inactive:
        query = query.where(CV.is_active.is_(True))
    cvs = db.scalars(query.order_by(CV.created_at.desc(), CV.id.desc())).all()
    if not cvs:
        return []

    cv_ids = [cv.id for cv in cvs]
    rows = db.execute(
        select(Analysis.cv_id, func.count(Analysis.id))
        .where(Analysis.cv_id.in_(cv_ids))
        .group_by(Analysis.cv_id)
    ).all()
    counts = {int(cv_id): int(count) for cv_id, count in rows if cv_id is not None}
    return [serialize_cv_response(cv, analysis_count=counts.get(cv.id, 0)) for cv in cvs]


def get_user_cv_detail(
    db: Session, user_id: int, cv_id: int, *, include_inactive: bool = False
) -> tuple[CVResponse, CVExtractionWarning | None]:
    cv = db.scalar(select(CV).where(CV.id == cv_id))
    if cv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    if cv.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this CV",
        )
    if not cv.is_active and not include_inactive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")

    analysis_count = int(
        db.scalar(select(func.count(Analysis.id)).where(Analysis.cv_id == cv.id)) or 0
    )
    cv_data = serialize_cv_response(cv, analysis_count=analysis_count)
    warning = build_cv_extraction_warning(cv)
    return cv_data, warning


def _safe_unlink_cv_file(file_path_str: str) -> None:
    try:
        resolved_root = UPLOAD_ROOT.resolve()
        resolved_file = Path(file_path_str).resolve()
        if resolved_root in resolved_file.parents:
            resolved_file.unlink(missing_ok=True)
    except Exception:
        logger.warning("Failed to remove deleted CV file from storage")


def delete_user_cv(db: Session, user_id: int, cv_id: int) -> tuple[CVDeleteData, str]:
    cv = db.scalar(select(CV).where(CV.id == cv_id))
    if cv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    if cv.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this CV",
        )
    if not cv.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV not found or already deleted",
        )

    analysis_count = int(
        db.scalar(select(func.count(Analysis.id)).where(Analysis.cv_id == cv.id)) or 0
    )

    if analysis_count > 0:
        cv.is_active = False
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while hiding CV",
            ) from exc
        return (
            CVDeleteData(
                cv_id=cv.id,
                deleted=True,
                deletion_type="soft",
                is_active=False,
                has_analysis=True,
                analysis_count=analysis_count,
            ),
            "CV da gan voi bao cao phan tich lich su nen da duoc xoa mem (an trang thai hoat dong).",
        )

    file_path_str = cv.file_path
    try:
        db.delete(cv)
        db.commit()
    except IntegrityError:
        db.rollback()
        cv = db.scalar(select(CV).where(CV.id == cv_id))
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
        cv.is_active = False
        db.commit()
        ref_count = int(
            db.scalar(select(func.count(Analysis.id)).where(Analysis.cv_id == cv.id)) or 1
        )
        return (
            CVDeleteData(
                cv_id=cv.id,
                deleted=True,
                deletion_type="soft",
                is_active=False,
                has_analysis=True,
                analysis_count=ref_count,
            ),
            "CV da gan voi bao cao phan tich lich su nen da duoc xoa mem (an trang thai hoat dong).",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while deleting CV",
        ) from exc

    _safe_unlink_cv_file(file_path_str)
    return (
        CVDeleteData(
            cv_id=cv_id,
            deleted=True,
            deletion_type="hard",
            is_active=False,
            has_analysis=False,
            analysis_count=0,
        ),
        "Da xoa CV thanh cong.",
    )
