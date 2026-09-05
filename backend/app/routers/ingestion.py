"""
Need to wire Azure document intelligence for OCR
#we are currently doing with pytesseract model but it lacks extracting data from handwritten image
One advantage of using Azure document intelligence is that
it maintains the hierarchial docuyment structure

whats map detection? - detecting boundaries on text, img and reconstructing them,


#Todo
1. First when a PDF with text and images are given , pytesseract is able to extract but the order varies/jumbled. Need to fix that
2. Handwritten images? - Wire Azure 


"""


import io
import shutil
import uuid
from pathlib import Path

import fitz  # PyMuPDF
import httpx
import pytesseract
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.orm import Session

from app.database import DATA_DIR, get_db
from app.models import IngestedItem, SourceType
from app.preprocessing import clean_text
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
    """Extract text page by page, preserving reading order. Walks each
    page's text/image blocks sorted top-to-bottom (left-to-right within a
    row) so a caption stays next to the image it describes instead of all
    native text being grouped before all OCR'd image text. Single-column
    layout assumption — not a general multi-column reading-order solver."""
    try:
        doc = fitz.open(stream=contents, filetype="pdf")
    except Exception:
        doc = None

    if doc is None:
        # Can't rasterize without PyMuPDF; fall back to plain pypdf text with
        # no ordering relative to images (nothing better is available).
        try:
            reader = PdfReader(io.BytesIO(contents))
            pages_text = [page.extract_text() or "" for page in reader.pages]
        except PdfReadError:
            return None
        return "\n\n".join(p.strip() for p in pages_text if p.strip()) or None

    results = []
    for page in doc:
        blocks = sorted(
            page.get_text("dict")["blocks"],
            key=lambda b: (round(b["bbox"][1]), b["bbox"][0]),
        )

        page_parts = []
        for block in blocks:
            if block["type"] == 0:
                block_text = "\n".join(
                    "".join(span["text"] for span in line["spans"])
                    for line in block["lines"]
                ).strip()
                if block_text:
                    page_parts.append(block_text)
            elif block["type"] == 1:
                # Render this block's own placed region (not the raw
                # embedded bytes, which can be pre-rotation/pre-scale and
                # OCR noticeably worse than the rendered, positioned image).
                try:
                    rect = fitz.Rect(block["bbox"])
                    pixmap = page.get_pixmap(clip=rect, dpi=200)
                    image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                    ocr_text = pytesseract.image_to_string(image).strip()
                    if ocr_text:
                        page_parts.append(ocr_text)
                except Exception:
                    continue

        if page_parts:
            results.append("\n".join(page_parts))

    doc.close()
    return "\n\n".join(results) or None


def extract_docx_text(contents: bytes) -> str | None:
    """Pull paragraph text and OCR of inline images in document order —
    each paragraph's own images are read from that paragraph's runs (where
    they structurally live in the OOXML), not from the document-wide flat
    relationship list, so an image embedded mid-paragraph comes out next to
    the text around it instead of all images being grouped at the end.
    Table content is appended after all paragraphs (not interleaved into
    exact body order)."""
    try:
        document = Document(io.BytesIO(contents))
    except Exception:
        return None

    parts = []

    for paragraph in document.paragraphs:
        para_text = paragraph.text.strip()
        if para_text:
            parts.append(para_text)

        for run in paragraph.runs:
            for blip in run._element.findall(".//" + qn("a:blip")):
                rId = blip.get(qn("r:embed"))
                if not rId:
                    continue
                try:
                    image_part = document.part.related_parts[rId]
                    image = Image.open(io.BytesIO(image_part.blob)).convert("RGB")
                    ocr_text = pytesseract.image_to_string(image).strip()
                    if ocr_text:
                        parts.append(ocr_text)
                except Exception:
                    continue

    table_lines = []
    for table in document.tables:
        for row in table.rows:
            cells_text = [cell.text.strip() for cell in row.cells]
            if any(cells_text):
                table_lines.append(" | ".join(cells_text))
    if table_lines:
        parts.append("\n".join(table_lines))

    return "\n\n".join(parts) or None


@router.post("/text", response_model=IngestedItemResponse, status_code=201)
def ingest_text(payload: TextIngestRequest, db: Session = Depends(get_db)):
    item = IngestedItem(
        title=payload.title,
        content=clean_text(payload.content),
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
    extracted_text = clean_text(" ".join(soup.get_text(separator=" ").split()))

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

    stored_name = f"{uuid.uuid4().hex}{extension}" #64 bit name for the file
    stored_path = UPLOAD_DIR / stored_name 
    stored_path.write_bytes(contents) #this basically stores an original content copy of whatever user uploads

    extracted_text = None
    if extension in {".txt", ".md"}:
        extracted_text = contents.decode("utf-8", errors="replace")
    elif extension == ".pdf":
        extracted_text = extract_pdf_text(contents)
    elif extension == ".docx":
        extracted_text = extract_docx_text(contents)

    extracted_text = clean_text(extracted_text)

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
    return db.query(IngestedItem).order_by(IngestedItem.created_at.desc()).all() #returns the ingested items in descending order by time
