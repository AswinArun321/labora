"""
Automatic lab record generation (slide 11).

Only approved submissions go into a record, and the output printed is always the
real stored execution result - never typed or invented.
"""
import io

from django.template.loader import render_to_string
from django.utils import timezone
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from accounts.models import CollegeSettings

from .models import Submission


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
        "title": p.title,
        "aim": p.aim,
        "language": p.get_language_display(),
        "code": sub.code,
        "stdin": stdin,
        "output": output or "(no output)",
        "result": sub.result or "The program was executed successfully and the output was verified.",
        "date": timezone.localtime(sub.submitted_at or sub.updated_at).strftime("%d-%m-%Y"),
        "approved_by": sub.approved_by.get_full_name() if sub.approved_by else "",
        "approved_on": timezone.localtime(sub.approved_at).strftime("%d-%m-%Y") if sub.approved_at else "",
    }


def record_context(student, subject, submissions):
    cs = CollegeSettings.load()
    return {
        "college": cs,
        "logo_path": cs.logo.path if cs.logo else None,
        "student": {
            "name": student.get_full_name() or student.username,
            "roll_no": student.roll_no,
            "batch": student.batch,
            "department": student.department.name if student.department else "",
        },
        "subject": {"name": subject.name, "code": subject.code, "semester": subject.semester,
                    "academic_year": subject.academic_year},
        "entries": [record_entry(s) for s in submissions],
    }


def _mono(paragraph, text):
    run = paragraph.add_run(text)
    run.font.name = "Courier New"
    run.font.size = Pt(9.5)
    return run


def build_docx(ctx) -> bytes:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    cs = ctx["college"]

    def header():
        if ctx["logo_path"]:
            try:
                doc.add_picture(ctx["logo_path"], width=Pt(60))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            except Exception:
                pass
        h = doc.add_paragraph()
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = h.add_run(cs.college_name.upper())
        r.bold = True
        r.font.size = Pt(15)
        if cs.college_address:
            a = doc.add_paragraph(cs.college_address)
            a.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Cover page
    header()
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = t.add_run(cs.record_title)
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
        doc.add_paragraph(cs.record_footer)

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
                para.add_run(body)
        sign = doc.add_paragraph()
        sign.add_run(f"\nApproved: {e['approved_on']}\t\t\tTeacher signature: ____________")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_pdf(ctx) -> bytes:
    from weasyprint import HTML  # imported lazily: needs system Pango libraries

    html = render_to_string("labs/record.html", ctx)
    return HTML(string=html).write_pdf()
