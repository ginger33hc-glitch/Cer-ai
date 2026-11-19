"""Render an immutable screening snapshot; never calculate clinical decisions."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reports import PDF_UNICODE_REGULAR, PDF_UNICODE_BOLD


def _score_rows(eye, tr):
    """Display canonical outputs only; do not calculate or revise clinical scores."""
    rows = []
    top = eye.get("topography") or {}
    measurements = eye.get("measurements") or {}
    rows.append(("Randleman/ERSS topography" if not tr else "Randleman/ERSS topografi",
                 f"I-S {measurements.get('I_S', '—')} D; SRAX {measurements.get('srax_deg', '—')}; category {top.get('category', '—')}; topography points {top.get('points', '—')}"))
    rows.append(("ERSS scope" if not tr else "ERSS kapsamı",
                 "Topography component only; NOT total surgical ERSS (age, MRSE, thickness, RSB excluded)."
                 if not tr else "Yalnız topografi bileşeni; toplam cerrahi ERSS DEĞİL (yaş, MRSE, kalınlık, RSB hariç)."))
    nice = eye.get("nice") or {}
    values, points = nice.get("values") or {}, nice.get("rows") or {}
    for label, value_key, point_key in (
        ("K2 (D)", "K2_D", "K2"),
        ("Central pachymetry (um)" if not tr else "Santral pakimetri (um)", "central_pachy_um", "central_pachymetry"),
        ("B.Ele.Th (um)", "B_Ele_Th_um", "B_Ele_Th"),
        ("I-S (D)", "I_S_D", "I_S"),
    ):
        rows.append((f"NICE {label}", f"{values.get(value_key, '—')} -> {points.get(point_key, '—')} {'puan' if tr else 'points'}"))
    rows.append(("NICE scoring bands" if not tr else "NICE puan eşikleri",
                 "K2: <45=1, 45–47=2, >47=3 D; central pachy: >520=1, 500–520=2, <500=3 um; B.Ele.Th: <=15.5=1, (15.5,18)=2, >=18=3 um; I-S: <1=1, 1–1.4=2, >1.4=3 D."
                 if not tr else "K2: <45=1, 45–47=2, >47=3 D; santral pakimetri: >520=1, 500–520=2, <500=3 um; B.Ele.Th: <=15,5=1, (15,5–18)=2, >=18=3 um; I-S: <1=1, 1–1,4=2, >1,4=3 D."))
    rows.append(("NICE total" if not tr else "NICE toplam", f"{nice.get('total', '—')} | {nice.get('category', '—')}"))
    ps3 = eye.get("ps3") or {}
    rows.append(("PS3 counts" if not tr else "PS3 sayımlar",
                 f"HIGH: {ps3.get('high_count', '—')} | MODERATE: {ps3.get('moderate_count', '—')} | complete: {ps3.get('complete', '—')}"))
    for finding in ps3.get("findings") or []:
        rows.append((f"PS3 {finding.get('key', '—')} [{finding.get('status', '—')}]", finding.get("detail", "—")))
    bad = eye.get("bad_d") or {}
    rows.append(("Final BAD-D", f"{bad.get('value', '—')} | {bad.get('classification', '—')}"))
    rows.append(("BAD-D thresholds" if not tr else "BAD-D eşikleri",
                 "normal <=1.60; suspicious >1.60 and <2.60; abnormal >=2.60"
                 if not tr else "normal <=1,60; şüpheli >1,60 ve <2,60; anormal >=2,60"))
    rows.append(("BAD-D context" if not tr else "BAD-D bağlam",
                 "Df/Db/Dp/Dt/Da/PPI/ARTmax are contextual, NOT added to Final D."
                 if not tr else "Df/Db/Dp/Dt/Da/PPI/ARTmax bağlamsaldır; Final D'ye EKLENMEZ."))
    for key, value in (bad.get("context") or {}).items():
        rows.append((f"BAD {key}", str(value) if value is not None else "—"))
    return rows


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
        story += [
            para(
                "Progresyon — hekim değerlendirmesi: Bu tek taramadan progresyon belirlenemez. Tarihi doğrulanmış seri tomografileri (Kmax, en ince pakimetri, ön/arka yüz ve varsa ABCD progresyonu), refraksiyon ve klinik muayene ile karşılaştırın. Pozitif tarama progresyon kanıtı değildir."
                if tr
                else "Progression — physician review: This single screening assessment cannot establish progression. Compare date-verified serial tomography (Kmax, thinnest pachymetry, anterior/posterior changes and ABCD progression when available), refraction and clinical examination. Positive screening does not prove progression."
            )
        ]
        story.append(para("Scoring breakdown (canonical clinical engine)" if not tr else "Puanlama ayrıntıları (kanonik klinik motor)", heading))
        score_table = Table(
            [[para(key), para(value)] for key, value in _score_rows(eye, tr)],
            colWidths=[175, 265],
            hAlign="LEFT",
            repeatRows=0,
        )
        score_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9e0e6")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.extend([score_table, Spacer(1, 10)])
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
