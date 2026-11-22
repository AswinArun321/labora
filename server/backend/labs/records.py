"""
Automatic lab record generation (slide 11).

Only approved submissions go into a record, and the output printed is always the
real stored execution result - never typed or invented.
"""
import io
import logging
import os
import pathlib
import re
import shutil
import subprocess
from typing import Optional

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Inches

from accounts.models import CollegeSettings
from .models import Submission

logger = logging.getLogger("labora.records")

# Regex to strip ANSI escape codes (e.g., color sequences \x1b[31m)
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

# Regex to strip XML 1.0 illegal control characters:
# Valid characters in XML 1.0: #x9 (\t) | #xA (\n) | #xD (\r) | [#x20-#xD7FF] | [#xE000-#xFFFD]
# Illegal: \x00-\x08, \x0b, \x0c, \x0e-\x1f, \x7f-\x84, \x86-\x9f
_XML_ILLEGAL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]")


def sanitize_xml_text(text: str) -> str:
    """
    Sanitizes string for XML 1.0 compatibility (required by python-docx and lxml).
    Strips ANSI escape sequences and XML-illegal control characters.
    Preserves valid tabs, newlines, carriage returns, and all Unicode (including Indian languages).
    """
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    # Strip ANSI escape sequences first
    cleaned = _ANSI_ESCAPE_RE.sub("", text)
    # Strip illegal XML control characters
    return _XML_ILLEGAL_RE.sub("", cleaned)


class PDFConverterUnavailableError(Exception):
    """Raised when neither LibreOffice nor WeasyPrint is available to generate PDFs."""
    pass


def record_entry(sub: Submission) -> dict:
    ex = sub.record_execution or sub.executions.filter(status="Accepted").order_by("-created_at").first()
    output = ""
    stdin = ""
    if ex:
        output = ex.stdout or ""
        if ex.stderr:
            output += ("\n" if output else "") + ex.stderr
        stdin = ex.stdin
    p = sub.practical
    return {
        "experiment_no": p.experiment_no,
        "title": sanitize_xml_text(p.title),
        "aim": sanitize_xml_text(p.aim),
        "language": p.get_language_display(),
        "code": sanitize_xml_text(sub.code),
        "stdin": sanitize_xml_text(stdin),
        "output": sanitize_xml_text(output) or "(no output)",
        "result": sanitize_xml_text(sub.result or "The program was executed successfully and the output was verified."),
        "date": timezone.localtime(sub.submitted_at or sub.updated_at).strftime("%d-%m-%Y"),
        "approved_by": sanitize_xml_text(sub.approved_by.get_full_name() if sub.approved_by else ""),
        "approved_on": timezone.localtime(sub.approved_at).strftime("%d-%m-%Y") if sub.approved_at else "",
    }


def record_context(student, subject, submissions):
    cs = CollegeSettings.load()
    logo_path = cs.logo.path if (cs.logo and hasattr(cs.logo, "path") and os.path.isfile(cs.logo.path)) else None
    return {
        "college": cs,
        "logo_path": logo_path,
        "student": {
            "name": sanitize_xml_text(student.get_full_name() or student.username),
            "roll_no": sanitize_xml_text(student.roll_no or ""),
            "batch": sanitize_xml_text(student.batch or ""),
            "department": sanitize_xml_text(student.department.name if student.department else ""),
        },
        "subject": {
            "name": sanitize_xml_text(subject.name),
            "code": sanitize_xml_text(subject.code),
            "semester": subject.semester,
            "academic_year": sanitize_xml_text(subject.academic_year or ""),
        },
        "entries": [record_entry(s) for s in submissions],
    }


def _mono(paragraph, text):
    run = paragraph.add_run(sanitize_xml_text(text))
    run.font.name = "Courier New"
    run.font.size = Pt(9.5)
    return run


def build_docx_document(ctx) -> Document:
    """Builds and returns a python-docx Document object with formatting and XML sanitization."""
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    cs = ctx["college"]

    def header():
        logo_path = ctx.get("logo_path")
        if logo_path and os.path.isfile(logo_path):
            try:
                doc.add_picture(logo_path, width=Pt(60))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            except Exception as e:
                logger.warning(f"Could not embed logo picture {logo_path}: {e}")
        h = doc.add_paragraph()
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        college_name = sanitize_xml_text(cs.college_name.upper())
        r = h.add_run(college_name)
        r.bold = True
        r.font.size = Pt(15)
        if cs.college_address:
            college_addr = sanitize_xml_text(cs.college_address)
            a = doc.add_paragraph(college_addr)
            a.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Cover page
    header()
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = t.add_run(sanitize_xml_text(cs.record_title))
    tr.bold = True
    tr.font.size = Pt(18)
    s, st = ctx["subject"], ctx["student"]
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for k, v in [("Name", st["name"]), ("Roll No", st["roll_no"]), ("Batch", st["batch"]),
                 ("Department", st["department"]), ("Subject", f"{s['code']} - {s['name']}"),
                 ("Semester", str(s["semester"])), ("Academic Year", s["academic_year"])]:
        row = table.add_row().cells
        row[0].text, row[1].text = k, v or ""
    doc.add_paragraph()
    doc.add_paragraph("INDEX").runs[0].bold = True
    idx = doc.add_table(rows=1, cols=4)
    idx.style = "Table Grid"
    for c, txt in zip(idx.rows[0].cells, ["Exp No", "Date", "Title", "Teacher Sign"]):
        c.text = txt
    for e in ctx["entries"]:
        r = idx.add_row().cells
        r[0].text, r[1].text, r[2].text, r[3].text = str(e["experiment_no"]), e["date"], e["title"], ""
    if cs.record_footer:
        doc.add_paragraph()
        doc.add_paragraph(sanitize_xml_text(cs.record_footer))

    for e in ctx["entries"]:
        doc.add_page_break()
        p = doc.add_paragraph()
        p.add_run(f"Experiment No: {e['experiment_no']}").bold = True
        p.add_run(f"\t\t\tDate: {e['date']}")
        h = doc.add_paragraph()
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        hr = h.add_run(e["title"].upper())
        hr.bold = True
        for label, body, mono in [("Aim", e["aim"], False), (f"Source Code ({e['language']})", e["code"], True)] + (
            [("Input", e["stdin"], True)] if e["stdin"].strip() else []
        ) + [("Output", e["output"], True), ("Result", e["result"], False)]:
            doc.add_paragraph().add_run(label + ":").bold = True
            para = doc.add_paragraph()
            if mono:
                _mono(para, body)
            else:
                para.add_run(sanitize_xml_text(body))
        sign = doc.add_paragraph()
        sign.add_run(f"\nApproved: {e['approved_on']}\t\t\tTeacher signature: ____________")

    return doc


def build_docx_file(ctx, output_path: str):
    """Generates DOCX and writes directly to output_path."""
    doc = build_docx_document(ctx)
    doc.save(output_path)


def build_docx(ctx) -> bytes:
    """Generates DOCX and returns raw bytes (backward compatibility)."""
    doc = build_docx_document(ctx)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def find_libreoffice_binary() -> Optional[str]:
    """
    Locates the LibreOffice/soffice executable dynamically across environments.
    Checks settings.LIBREOFFICE_PATH, system PATH, and standard Windows/Linux install locations.
    """
    custom = getattr(settings, "LIBREOFFICE_PATH", "")
    if custom and os.path.isfile(custom):
        return custom

    # System PATH lookup
    for bin_name in ["soffice", "libreoffice", "soffice.bin", "soffice.exe"]:
        found = shutil.which(bin_name)
        if found:
            return found

    # OS-specific standard paths
    if os.name == "nt":
        candidates = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
    else:
        candidates = [
            "/usr/bin/soffice",
            "/usr/bin/libreoffice",
            "/usr/local/bin/soffice",
            "/usr/local/bin/libreoffice",
        ]

    for c in candidates:
        if os.path.isfile(c):
            return c

    return None


def convert_docx_to_pdf_libreoffice(docx_path: str, output_dir: str, timeout: int = 30) -> str:
    """
    Converts a DOCX file to PDF using headless LibreOffice.
    Uses an isolated user profile per execution to prevent multi-process collisions.
    Validates output PDF and returns the path to the converted PDF.
    """
    lo_bin = find_libreoffice_binary()
    if not lo_bin:
        raise FileNotFoundError("LibreOffice binary not found.")

    profile_dir = os.path.join(output_dir, "lo_profile")
    os.makedirs(profile_dir, exist_ok=True)
    profile_uri = pathlib.Path(profile_dir).as_uri()

    cmd = [
        lo_bin,
        "--headless",
        "--invisible",
        "--nocrashreport",
        "--nodefault",
        "--nofirststartwizard",
        "--nolockcheck",
        "--nologo",
        "--norestore",
        f"-env:UserInstallation={profile_uri}",
        "--convert-to", "pdf:writer_pdf_Export",
        "--outdir", output_dir,
        docx_path,
    ]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"LibreOffice conversion timed out after {timeout} seconds.") from exc

    expected_pdf_name = os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
    output_pdf_path = os.path.join(output_dir, expected_pdf_name)

    if not os.path.isfile(output_pdf_path) or os.path.getsize(output_pdf_path) == 0:
        err_msg = proc.stderr.decode("utf-8", errors="replace").strip() or proc.stdout.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"LibreOffice failed to generate PDF (exit code {proc.returncode}): {err_msg}")

    # Validate PDF header (%PDF)
    with open(output_pdf_path, "rb") as f:
        header = f.read(5)
        if not header.startswith(b"%PDF"):
            raise ValueError("Converted file is not a valid PDF document.")

    return output_pdf_path


def build_pdf_weasyprint(ctx, output_pdf_path: str) -> str:
    """
    Converts record HTML template to PDF using WeasyPrint.
    Ensures logo URL is properly formatted for HTML engine.
    """
    from weasyprint import HTML  # lazy import: needs system Pango libraries

    ctx_copy = dict(ctx)
    logo_path = ctx_copy.get("logo_path")
    if logo_path and os.path.isfile(logo_path):
        ctx_copy["logo_uri"] = pathlib.Path(logo_path).as_uri()
    else:
        ctx_copy["logo_uri"] = None

    html = render_to_string("labs/record.html", ctx_copy)
    HTML(string=html).write_pdf(output_pdf_path)

    if not os.path.isfile(output_pdf_path) or os.path.getsize(output_pdf_path) == 0:
        raise RuntimeError("WeasyPrint produced an empty or missing PDF file.")

    with open(output_pdf_path, "rb") as f:
        if not f.read(5).startswith(b"%PDF"):
            raise ValueError("WeasyPrint output is not a valid PDF document.")

    return output_pdf_path


def build_pdf_file(ctx, output_dir: str, filename: str) -> str:
    """
    Builds a PDF file into output_dir based on configured converter strategy:
    - 'libreoffice': uses LibreOffice only.
    - 'weasyprint': uses WeasyPrint only.
    - 'auto' (default): tries LibreOffice first; falls back to WeasyPrint.
    """
    strategy = getattr(settings, "DOCX_PDF_CONVERTER", "auto").lower()
    timeout = getattr(settings, "RECORD_GENERATION_TIMEOUT_SECONDS", 30)

    if strategy in ("libreoffice", "auto"):
        lo_bin = find_libreoffice_binary()
        if lo_bin:
            try:
                docx_path = os.path.join(output_dir, f"{filename}.docx")
                build_docx_file(ctx, docx_path)
                return convert_docx_to_pdf_libreoffice(docx_path, output_dir, timeout=timeout)
            except Exception as lo_err:
                logger.warning(f"LibreOffice conversion failed: {lo_err}")
                if strategy == "libreoffice":
                    raise

    if strategy in ("weasyprint", "auto"):
        try:
            pdf_path = os.path.join(output_dir, f"{filename}.pdf")
            return build_pdf_weasyprint(ctx, pdf_path)
        except (ImportError, OSError) as wp_err:
            logger.warning(f"WeasyPrint unavailable: {wp_err}")
            if strategy == "weasyprint":
                raise

    raise PDFConverterUnavailableError(
        "PDF generation is currently unavailable on this server. "
        "Neither LibreOffice nor WeasyPrint native libraries are installed. "
        "Please download the DOCX version instead."
    )


def build_pdf(ctx) -> bytes:
    """Generates PDF and returns raw bytes (backward compatibility)."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix="labora_pdf_bytes_") as tmp_dir:
        pdf_path = build_pdf_file(ctx, tmp_dir, "record")
        with open(pdf_path, "rb") as f:
            return f.read()
