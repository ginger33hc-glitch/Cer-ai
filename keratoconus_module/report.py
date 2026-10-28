"""Render an immutable screening snapshot; never calculate clinical decisions."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reports import PDF_UNICODE_REGULAR, PDF_UNICODE_BOLD


def build_screening_pdf(snapshot):
    tr = snapshot.get("locale") == "tr"
    labels = {
        "NEGATIVE": "Negatif" if tr else "Negative",
        "SUSPICIOUS": "Şüpheli" if tr else "Suspicious",
        "POSITIVE": "Pozitif" if tr else "Positive",
        "NOT_ASSESSABLE": "Değerlendirilemedi" if tr else "Not assessable",
    }
    body = ParagraphStyle(
        "KCBody", fontName=PDF_UNICODE_REGULAR, fontSize=9, leading=13, spaceAfter=6
    )
    title = ParagraphStyle(
        "KCTitle",
        parent=body,
        fontName=PDF_UNICODE_BOLD,
        fontSize=17,
        leading=22,
        textColor=colors.HexColor("#173b57"),
    )
    heading = ParagraphStyle(
        "KCHeading", parent=title, fontSize=12, leading=16, spaceBefore=10
    )
    para = lambda value, style=body: Paragraph(escape(str(value)), style)
    stream = BytesIO()
    doc = SimpleDocTemplate(
        stream,
        pagesize=A4,
        leftMargin=38,
        rightMargin=38,
        topMargin=32,
        bottomMargin=32,
    )
    story = [
        para(
            "CER-AI — Keratokonus Tarama" if tr else "CER-AI — Keratoconus Screening",
            title,
        )
    ]
    patient = snapshot.get("patient") or {}
    story += [
        para(
            f"{patient.get('name') or '—'} | {'Yaş' if tr else 'Age'}: {patient.get('age', '—')} | {patient.get('report_date') or ''} | {patient.get('reviewer') or ''}"
        )
    ]
    notice = (
        "Tarama karar desteğidir. Pozitif sonuç kesin keratokonus tanısı değildir; negatif sonuç hastalığı dışlamaz. Bulgular göz hekimi tarafından değerlendirilmelidir."
        if tr
        else snapshot.get("notice", "")
    )
    story += [para(notice)]
    for eye in snapshot.get("eyes", []):
        story += [para(f"{eye['eye']} — {labels[eye['screening_result']]}", heading)]
        ref = eye.get("refraction") or {}
        story += [
            para(
                f"S / C / Axis: {ref.get('manifest_entered_sphere_D', '—')} / {ref.get('manifest_cylinder_signed_D', '—')} / {ref.get('manifest_axis_deg', '—')}"
            )
        ]
        story += [para(finding["detail"]) for finding in eye.get("findings", [])]
        if eye.get("missing"):
            story += [
                para(
                    ("Eksik / doğrulama: " if tr else "Missing / verification: ")
                    + ", ".join(eye["missing"])
                )
            ]
        rows = [
            [para(key), para(value)]
            for key, value in (eye.get("measurements") or {}).items()
        ]
        if rows:
            table = Table(rows, colWidths=[330, 110], hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        (
                            "LINEBELOW",
                            (0, 0),
                            (-1, -1),
                            0.3,
                            colors.HexColor("#d9e0e6"),
                        ),
                    ]
                )
            )
            story += [table, Spacer(1, 10)]
    for warning in list(snapshot.get("issues", [])) + list(
        snapshot.get("warnings", [])
    ):
        story.append(para(warning))
    story.append(para(str(snapshot.get("versions", {}))))
    doc.build(story)
    return stream.getvalue()
