import fitz  # PyMuPDF
from pathlib import Path
from config import CHUNK_SIZE, CHUNK_OVERLAP


def extract_text(pdf_path: Path) -> str:
    """Extract full text from a PDF."""
    doc = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def extract_sections(pdf_path: Path) -> dict[str, str]:
    """
    Attempt to split by common section headers.
    Falls back to chunking if structure isn't clear.
    """
    text = extract_text(pdf_path)
    
    section_markers = [
        "Abstract", "Introduction", "Related Work",
        "Background", "Method", "Methodology",
        "Experiments", "Results", "Discussion",
        "Conclusion", "Limitations", "Future Work"
    ]
    
    sections = {}
    lines = text.split("\n")
    current_section = "preamble"
    current_lines = []
    
    for line in lines:
        stripped = line.strip()
        matched = False
        for marker in section_markers:
            if stripped.lower().startswith(marker.lower()) and len(stripped) < 60:
                if current_lines:
                    sections[current_section] = "\n".join(current_lines)
                current_section = marker
                current_lines = []
                matched = True
                break
        if not matched:
            current_lines.append(line)
    
    if current_lines:
        sections[current_section] = "\n".join(current_lines)
    
    return sections


def chunk_text(text: str) -> list[str]:
    """
    Split text into overlapping chunks for embedding.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks