import io
import shutil
import uuid
from pathlib import Path

import fitz  # PyMuPDF
import httpx
import pytesseract
from bs4 import BeautifulSoup
from docx import Document
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.orm import Session

from app.database import DATA_DIR, get_db
from app.models import IngestedItem, SourceType
from app.schemas import IngestedItemResponse, TextIngestRequest, UrlIngestRequest

router = APIRouter(prefix="/ingest", tags=["ingestion"])

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# The pip package only wraps the Tesseract binary; if it's not resolvable on
# PATH yet (e.g. installed after this shell session started), fall back to
# the default Windows install location instead of failing every OCR call.
if shutil.which("tesseract") is None:
    _default_tesseract = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if _default_tesseract.exists():
        pytesseract.pytesseract.tesseract_cmd = str(_default_tesseract)


def extract_pdf_text(contents: bytes) -> str | None:
    """Extract text per page: keep the native text layer if present, AND
    independently OCR every embedded image on the page (a page can have
    both). Falls back to OCR-ing a full-page render only when a page has
    neither native text nor any discrete embedded image."""
    try:
        reader = PdfReader(io.BytesIO(contents)) #PdfReader is a function of pypdf . it can pull only embedded text not images/ other text as pictures
        native_pages = [page.extract_text() or "" for page in reader.pages] #gets all pages with the typed content
    except PdfReadError:
        native_pages = []

    try:
        doc = fitz.open(stream=contents, filetype="pdf") #part of pymupdf . rasterize pages/images for OCR
    except Exception:
        doc = None

    page_count = len(doc) if doc is not None else len(native_pages)

    results = []
    for i in range(page_count): #this can range from nativer pages to len(doc)
        page_parts = []

        native = native_pages[i].strip() if i < len(native_pages) else ""
        if native:
            page_parts.append(native)

        if doc is not None:
            page = doc[i]
            images = page.get_images(full=True)
            if images and native:
                # Page already has native text: OCR just the image regions,
                # rendered at their placed position/orientation on the page
                # (not the raw embedded bytes, which can be pre-rotation/
                # pre-scale and OCR noticeably worse).
                for img_info in images:
                    xref = img_info[0]
                    try:
                        for rect in page.get_image_rects(xref):
                            pixmap = page.get_pixmap(clip=rect, dpi=200)
                            image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                            ocr_text = pytesseract.image_to_string(image).strip()
                            if ocr_text:
                                page_parts.append(ocr_text)
                    except Exception:
                        continue
            elif not native:
                # No native text at all: OCR the full page render. More
                # robust than per-image extraction for scanned pages.
                try:
                    pixmap = page.get_pixmap(dpi=200)
                    rendered = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                    ocr_text = pytesseract.image_to_string(rendered).strip()
                    if ocr_text:
                        page_parts.append(ocr_text)
                except Exception:
                    pass

        if page_parts:
            results.append("\n".join(page_parts))

    if doc is not None:
        doc.close()

    return "\n\n".join(results) or None


def extract_docx_text(contents: bytes) -> str | None:
    """Pull paragraph text, table text, and OCR of any embedded images."""
    try:
        document = Document(io.BytesIO(contents))
    except Exception:
        return None

    parts = []

    paragraphs_text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
    if paragraphs_text:
        parts.append(paragraphs_text)

    table_lines = []
    for table in document.tables:
        for row in table.rows:
            cells_text = [cell.text.strip() for cell in row.cells]
            if any(cells_text):
                table_lines.append(" | ".join(cells_text))
    if table_lines:
        parts.append("\n".join(table_lines))

    for rel in document.part.rels.values():
        if "image" not in rel.reltype:
            continue
        try:
            image = Image.open(io.BytesIO(rel.target_part.blob)).convert("RGB")
            ocr_text = pytesseract.image_to_string(image).strip()
            if ocr_text:
                parts.append(ocr_text)
        except Exception:
            continue

    return "\n\n".join(parts) or None


@router.post("/text", response_model=IngestedItemResponse, status_code=201)
def ingest_text(payload: TextIngestRequest, db: Session = Depends(get_db)):
    item = IngestedItem(
        title=payload.title,
        content=payload.content,
        tags=payload.tags,
        source_type=SourceType.text,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/url", response_model=IngestedItemResponse, status_code=201)
async def ingest_url(payload: UrlIngestRequest, db: Session = Depends(get_db)):
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client: #network call is made
            resp = await client.get(str(payload.url))
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {exc}")

    soup = BeautifulSoup(resp.text, "html.parser") #beautifyl soup parses the html and formulates like a tree
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    page_title = soup.title.string.strip() if soup.title and soup.title.string else None
    extracted_text = " ".join(soup.get_text(separator=" ").split())

    item = IngestedItem(
        title=payload.title or page_title or str(payload.url),
        content=extracted_text,
        tags=payload.tags,
        source_type=SourceType.url,
        source_url=str(payload.url),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/file", response_model=IngestedItemResponse, status_code=201)
async def ingest_file(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    tags: str | None = Form(None),
    db: Session = Depends(get_db),
):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 20MB limit")

    stored_name = f"{uuid.uuid4().hex}{extension}"
    stored_path = UPLOAD_DIR / stored_name
    stored_path.write_bytes(contents)

    extracted_text = None
    if extension in {".txt", ".md"}:
        extracted_text = contents.decode("utf-8", errors="replace")
    elif extension == ".pdf":
        extracted_text = extract_pdf_text(contents)
    elif extension == ".docx":
        extracted_text = extract_docx_text(contents)

    item = IngestedItem(
        title=title or file.filename or stored_name,
        content=extracted_text,
        tags=tags,
        source_type=SourceType.file,
        file_path=str(stored_path.relative_to(DATA_DIR.parent)),
        original_filename=file.filename,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[IngestedItemResponse])
def list_ingested_items(db: Session = Depends(get_db)):
    return db.query(IngestedItem).order_by(IngestedItem.created_at.desc()).all()
