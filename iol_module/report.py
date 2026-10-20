"""One-page IOL report. Render existing results; never recalculate lens power."""
from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
from math import cos, sin, radians, isfinite
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

import reportlab
from pydantic import Field, model_validator
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from .models import IOLPowerPlan, IOLRecommendation, StrictModel

for name, filename in (("IOL-Regular", "Vera.ttf"), ("IOL-Bold", "VeraBd.ttf")):
    pdfmetrics.registerFont(TTFont(name, str(Path(reportlab.__file__).parent / "fonts" / filename)))
pdfmetrics.registerFontFamily("IOL-Regular", normal="IOL-Regular", bold="IOL-Bold")


class ReportEye(StrictModel):
    eye: Literal["OD", "OS"]
    plan: IOLPowerPlan
    recommendation: IOLRecommendation

    @model_validator(mode="after")
    def matching_eye(self):
        if self.plan.inputs.get("eye") != self.eye or self.recommendation.eye != self.eye:
            raise ValueError("Report eye does not match calculation and recommendation.")
        for key, value in (("k1_d", self.recommendation.active_k1_d),
                           ("k2_d", self.recommendation.active_k2_d),
                           ("k1_axis_deg", self.recommendation.k1_axis_deg),
                           ("k2_axis_deg", self.recommendation.k2_axis_deg)):
            if self.plan.inputs.get(key) != value:
                raise ValueError("Report measurements do not match the recommendation.")
        return self


class IOLReportInput(StrictModel):
    patient_name: str = Field(min_length=1, max_length=200)
    patient_age_years: int = Field(ge=18, le=120)
    locale: Literal["en", "tr"] = "en"
    eyes: list[ReportEye] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def matching_patient(self):
        if len({item.eye for item in self.eyes}) != len(self.eyes):
            raise ValueError("Duplicate report eye.")
        if any(item.recommendation.patient_name != self.patient_name for item in self.eyes):
            raise ValueError("Report patient does not match the recommendation.")
        return self


# Presentation labels only: thresholds and clinical decisions stay in engine.py.
WARNINGS = {
    "WARN_RETINA_SIGNIFICANT": ("Significant retinal disease; multifocal excluded", "Belirgin retina hastalığı; multifokal dışlandı"),
    "WARN_RETINA_MILD": ("Mild retinal disease: review", "Hafif retina hastalığı: değerlendirin"),
    "WARN_MACULAR_PATHOLOGY": ("Macular pathology; multifocal excluded", "Makula patolojisi; multifokal dışlandı"),
    "WARN_GLAUCOMA_PRESENT": ("Definite glaucoma; multifocal excluded", "Kesin glokom; multifokal dışlandı"),
    "WARN_GLAUCOMA_SUSPECT": ("Glaucoma suspect: review", "Glokom şüphesi: değerlendirin"),
    "WARN_OCULAR_SURFACE_MILD": ("Mild ocular surface disease: optimize", "Hafif oküler yüzey hastalığı: tedavi edin"),
    "WARN_OCULAR_SURFACE_MODERATE": ("Active ocular surface disease; multifocal excluded", "Aktif oküler yüzey hastalığı; multifokal dışlandı"),
    "WARN_OCULAR_SURFACE_SIGNIFICANT": ("Significant ocular surface disease; multifocal excluded", "Belirgin oküler yüzey hastalığı; multifokal dışlandı"),
    "WARN_HOA_HIGH": ("High HOA; multifocal excluded", "Yüksek HOA; multifokal dışlandı"),
    "WARN_HOA_MODERATE": ("Moderate HOA: review", "Orta düzey HOA: değerlendirin"),
    "WARN_KAPPA_HIGH_SURGEON_REVIEW": ("High kappa: surgeon review", "Yüksek kappa: cerrah değerlendirmesi"),
    "WARN_ALPHA_HIGH_SURGEON_REVIEW": ("High alpha: surgeon review", "Yüksek alfa: cerrah değerlendirmesi"),
    "WARN_PUPIL_TOO_SMALL": ("Small pupil; multifocal excluded", "Küçük pupil; multifokal dışlandı"),
    "WARN_PUPIL_TOO_LARGE": ("Large pupil; multifocal excluded", "Büyük pupil; multifokal dışlandı"),
    "WARN_IRREGULAR_ASTIGMATISM": ("Irregular astigmatism; multifocal excluded", "Düzensiz astigmatizma; multifokal dışlandı"),
}


def numeric(value):
    return type(value) in (int, float) and isfinite(value)


def fmt(value, digits=2):
    return f"{value:.{digits}f}" if numeric(value) else "-"


def selected_values(plan):
    """Do not invent a selected power, model or axis for incomplete results."""
    best = [p for p in plan.predictions if p.get("IsBestOption") is True]
    spherical = best[0] if len(best) == 1 and all(numeric(best[0].get(k)) for k in ("IOL", "Rx")) else None
    toric = None
    if plan.toric_status == "TEST_ONLY" and plan.calculation_status == "TEST_ONLY" and spherical and plan.toric_candidates:
        first = plan.toric_candidates[0]
        keys = ("spherical_equivalent_iol_d", "cylinder_iol_d", "marker_axis_deg",
                "residual_spectacle_cylinder_d", "residual_spectacle_axis_deg")
        if not all(numeric(first.get(k)) for k in keys) or not isinstance(first.get("model"), str):
            raise ValueError("Invalid toric report values.")
        if not 0 <= first["marker_axis_deg"] <= 180 or not 0 <= first["residual_spectacle_axis_deg"] <= 180:
            raise ValueError("Invalid toric report axis.")
        if first["spherical_equivalent_iol_d"] != spherical["IOL"]:
            raise ValueError("Toric and spherical report powers do not match.")
        toric = first
    if plan.calculation_status in {"EXTERNAL_REQUIRED", "CALCULATION_UNAVAILABLE"} and not plan.predictions:
        spherical = None
    return spherical, toric


def axis_endpoints(cx, cy, radius, axis):
    """Anterior view: 0 degrees right, 90 superior; identical scale for OD/OS."""
    dx, dy = radius * cos(radians(axis)), radius * sin(radians(axis))
    return cx - dx, cy - dy, cx + dx, cy + dy


def draw_eye(canvas, eye, x, top, axis, tr, radius=105):
    """Large, centered anterior-view axis diagram below the written findings."""
    cx, cy = x, top - radius - 16
    canvas.setStrokeColor(colors.HexColor("#9babb6")); canvas.setLineWidth(1)
    canvas.setFillColor(colors.HexColor("#f8fafb"))
    canvas.circle(cx, cy, radius, stroke=1, fill=1)
    canvas.setStrokeColor(colors.HexColor("#dce5e8"))
    canvas.circle(cx, cy, radius * .62, stroke=1, fill=0)
    canvas.circle(cx, cy, radius * .32, stroke=1, fill=0)
    # Pale iris and pupil; surgical axis remains prominent.
    # Low-contrast iris with radial texture instead of a target-like bullseye.
    canvas.setFillColor(colors.HexColor("#f0f4f5"))
    canvas.circle(cx, cy, radius * .57, stroke=0, fill=1)
    canvas.setStrokeColor(colors.HexColor("#e2e9eb")); canvas.setLineWidth(.45)
    for tick in range(0, 360, 10):
        a = radians(tick)
        canvas.line(cx + radius*.30*cos(a), cy + radius*.30*sin(a),
                    cx + radius*.54*cos(a), cy + radius*.54*sin(a))
    canvas.setFillColor(colors.HexColor("#dfe6e8"))
    canvas.circle(cx, cy, radius * .22, stroke=0, fill=1)
    canvas.line(cx-radius, cy, cx+radius, cy)
    canvas.line(cx, cy-radius, cx, cy+radius)
    canvas.setFont("IOL-Regular", 9); canvas.setFillColor(colors.HexColor("#173b57"))
    canvas.drawCentredString(cx, cy+radius+11, tr("SUPERIOR", "ÜST") + " 90°")
    canvas.drawCentredString(cx, cy-radius-16, tr("INFERIOR", "ALT"))
    canvas.drawCentredString(cx-radius-39, cy+5, "TEMPORAL" if eye == "OD" else tr("NASAL", "NAZAL"))
    canvas.drawCentredString(cx+radius+39, cy+5, tr("NASAL", "NAZAL") if eye == "OD" else "TEMPORAL")
    canvas.drawCentredString(cx-radius-19, cy-12, "180°")
    canvas.drawCentredString(cx+radius+19, cy-12, "0°")
    if axis is not None:
        canvas.setStrokeColor(colors.HexColor("#1f5e8c")); canvas.setLineWidth(3)
        canvas.setDash(6, 4); canvas.line(*axis_endpoints(cx, cy, radius, axis)); canvas.setDash()
        canvas.setFillColor(colors.HexColor("#1f5e8c"))
        x1, y1, x2, y2 = axis_endpoints(cx, cy, radius-7, axis)
        canvas.circle(x1, y1, 4, fill=1, stroke=0)
        canvas.circle(x2, y2, 4, fill=1, stroke=0)
    # Subtle frontal half-nose on the nasal side, mirrored for OD/OS.
    nasal = 1 if eye == "OD" else -1
    nx = cx + nasal * (radius + 60)
    canvas.setStrokeColor(colors.HexColor("#e6eaec")); canvas.setLineWidth(4)
    nose = canvas.beginPath()
    nose.moveTo(nx + nasal*10, cy + radius*.7)
    nose.curveTo(nx + nasal*15, cy + radius*.15, nx + nasal*38, cy-radius*.12, nx + nasal*18, cy-radius*.40)
    nose.curveTo(nx + nasal*8, cy-radius*.52, nx - nasal*10, cy-radius*.45, nx - nasal*13, cy-radius*.36)
    canvas.drawPath(nose, stroke=1, fill=0)
    canvas.setFont("IOL-Regular", 9)
    canvas.drawCentredString(cx, cy-radius-32, tr("Anterior view", "Önden görünüm"))


def build_iol_report(report: IOLReportInput, surgeon: str = "", *, report_date: str | None = None,
                     versions: dict | None = None) -> bytes:
    from .provenance import current_versions
    versions = current_versions() if versions is None else versions
    tr = lambda en, turkish: turkish if report.locale == "tr" else en
    width, height = A4
    left, content_width = 34, width-68
    ink, navy = colors.HexColor("#17212b"), colors.HexColor("#173b57")

    def paragraph(text, size=9, bold=False, color=ink):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), ParagraphStyle(
            "iol", fontName="IOL-Bold" if bold else "IOL-Regular", fontSize=size,
            leading=size*1.32, textColor=color, splitLongWords=True))

    def row(label, value):
        return f"{label}: {value}"

    sections = []
    for item in sorted(report.eyes, key=lambda item: item.eye):
        p, inp = item.plan, item.plan.inputs
        sphere, toric = selected_values(p)
        lines = [row(tr("Lens family", "Lens ailesi"), p.selected_lens_name)]
        lines.append(row(tr("Spherical equivalent" if p.route == "MANUFACTURER_TORIC" else "Spherical IOL power",
                            "Sferik eşdeğer" if p.route == "MANUFACTURER_TORIC" else "Sferik IOL gücü"), fmt(sphere["IOL"]) + " D" if sphere else tr("Not calculated", "Hesaplanmadı")))
        if toric:
            lines += [row(tr("Toric model", "Torik model"), toric["model"]),
                      row(tr("IOL-plane cylinder", "IOL düzleminde silindir"), fmt(toric["cylinder_iol_d"]) + " D"),
                      row(tr("Marker axis", "İşaret aksı"), fmt(toric["marker_axis_deg"], 1) + "°"),
                      row(tr("Residual cylinder (spectacle)", "Rezidüel silindir (gözlük)"), fmt(toric["residual_spectacle_cylinder_d"]) + " D / " + fmt(toric["residual_spectacle_axis_deg"], 1) + "°")]
        elif p.route == "MANUFACTURER_TORIC":
            lines.append(tr("Toric model / axis: NOT AVAILABLE", "Torik model / aks: HESAPLANMADI"))
        lines += [row(tr("Target / predicted refraction", "Hedef / beklenen refraksiyon"), fmt(p.target_refraction_d) + " D / " + (fmt(sphere["Rx"]) + " D" if sphere else "-")),
                  row(tr("Formula / A constant", "Formül / A sabiti"), (p.spherical_formula or p.calculator_name) + " / " + fmt(p.a_constant))]
        measurements = "   |   ".join(["AL " + fmt(inp.get("axial_length_mm")) + " mm", "ACD " + fmt(inp.get("acd_mm")) + " mm",
            "K1 " + fmt(inp.get("k1_d")) + " D / " + fmt(inp.get("k1_axis_deg"), 1) + "°",
            "K2 " + fmt(inp.get("k2_d")) + " D / " + fmt(inp.get("k2_axis_deg"), 1) + "°"])
        if inp.get("incision_axis_deg") is not None:
            measurements += "\n" + row(tr("Incision", "Kesi"), fmt(inp["incision_axis_deg"], 1) + "°") + "   |   SIA " + fmt(inp.get("sia_d")) + " D / " + fmt(inp.get("sia_axis_deg"), 1) + "°"
        posterior = inp.get("posterior_cornea")
        if isinstance(posterior, dict):
            measurements += "\n" + tr("Posterior K1/K2", "Arka kornea K1/K2") + ": " + fmt(posterior.get("k1_d")) + " / " + fmt(posterior.get("k2_d")) + " D; " + tr("axes", "akslar") + " " + fmt(posterior.get("k1_axis_deg"), 1) + " / " + fmt(posterior.get("k2_axis_deg"), 1) + "°   |   CCT " + fmt(inp.get("cct_um"), 0) + " µm"
        warnings = []
        if toric:
            warnings.append(tr("TEST ONLY: unvalidated toric prototype. Verify model, power, axis and residual independently with the manufacturer calculator before clinical use.",
                               "TEST ONLY: klinik doğrulaması yapılmamış torik prototip. Klinik kullanım öncesi model, güç, aks ve rezidüeli üretici hesaplayıcısıyla bağımsız doğrulayın."))
        if p.calculation_status == "EXTERNAL_REQUIRED":
            warnings.append(tr("External post-corneal-surgery calculation required; no implant power selected.", "Kornea cerrahisi sonrası harici hesaplama gerekli; implant gücü seçilmedi."))
        if p.route == "MANUFACTURER_TORIC" and toric is None:
            warnings.append(tr("Toric result unavailable. Complete measurements / verify the lens series and use the manufacturer calculator.", "Torik sonuç yok. Eksik ölçümleri tamamlayın / lens serisini doğrulayın ve üretici hesaplayıcısını kullanın."))
        if sphere is None:
            warnings.append(tr("No unique calculated spherical power. Complete the calculation at ESCRS.", "Tek bir hesaplanmış sferik güç yok. Hesaplamayı ESCRS'de tamamlayın."))
        if p.required_inputs:
            warnings.append(tr("Measured lens thickness is required.", "Ölçülmüş lens kalınlığı gerekli."))
        if p.fallback_reason:
            warnings.append(tr("Cooke K6 unavailable; local T2 fallback used.", "Cooke K6 kullanılamadı; yerel T2 ile hesaplandı."))
        if p.second_formula_required:
            warnings.append(tr("Independent verification with a second modern formula required (ESCRS).", "İkinci modern formülle bağımsız doğrulama gerekli (ESCRS)."))
        for code in item.recommendation.warning_codes:
            warnings.append(tr(*WARNINGS[code]) if code in WARNINGS else code)
        sections.append((item, toric, lines, measurements, " · ".join(warnings)))

    # Every eye receives its own full A4 page, even in bilateral reports.
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=A4, invariant=1)
    canvas.setTitle("CER-AI IOL report")
    canvas.setAuthor("CER-AI")
    now = datetime.now(ZoneInfo("Europe/Istanbul"))
    for item, toric, lines, measurements, warnings in sections:
        p = item.plan
        for size, diagram_radius in ((12, 112), (11, 100), (10, 88), (9, 76), (8, 62), (7.5, 52), (7, 48), (6.5, 44)):
            diagram_height = 2 * diagram_radius + 56
            header = paragraph(row(tr("Patient", "Hasta"), report.patient_name) + "   |   " +
                               row(tr("Age", "Yaş"), report.patient_age_years) + "\n" +
                               row(tr("Surgeon", "Cerrah"), surgeon or tr("Not recorded", "Kaydedilmedi")), size)
            header_height = header.wrap(content_width, height)[1]
            values = paragraph("\n".join(lines), size+1, bold=True, color=navy)
            values_height = values.wrap(content_width, height)[1]
            bio = paragraph(measurements, size)
            bio_height = bio.wrap(content_width, height)[1]
            warning = paragraph(warnings, size-1, color=colors.HexColor("#754600")) if warnings else None
            warning_height = warning.wrap(content_width-14, height)[1] if warning else 0
            total = header_height + 87 + (91 if toric else 27) + values_height + 9 + bio_height + 10 + diagram_height + warning_height + (18 if warning else 6) + 8
            if total <= height-76:
                break
        else:
            raise ValueError("Report content does not fit one readable A4 page. Please review the report data.")

        canvas.setFillColor(navy); canvas.setFont("IOL-Bold", 17)
        canvas.drawString(left, height-42, tr("CER-AI | IOL surgical plan", "CER-AI | IOL cerrahi planı"))
        canvas.setFont("IOL-Regular", 8)
        canvas.drawRightString(width-left, height-58, (report_date or now.strftime("%d.%m.%Y %H:%M")) + " (UTC+03:00)")
        header.drawOn(canvas, left, height-77-header_height)
        top = height-87-header_height
        canvas.setStrokeColor(colors.HexColor("#c7d5de")); canvas.setLineWidth(.7)
        canvas.line(left, top, width-left, top)
        canvas.setFont("IOL-Bold", 14); canvas.setFillColor(colors.HexColor("#147d52"))
        canvas.drawString(left, top-19, tr("RIGHT EYE - OD", "SAĞ GÖZ - OD") if item.eye == "OD" else tr("LEFT EYE - OS", "SOL GÖZ - OS"))
        if toric:
            canvas.setFont("IOL-Bold", 10)
            canvas.drawRightString(width-left, top-19, "TEST ONLY")
        if toric:
            canvas.setFillColor(colors.HexColor("#147d52")); canvas.setFont("IOL-Bold", 14)
            canvas.drawString(left, top-39, p.selected_lens_name[:62])
            # Three equally sized green surgical identifiers; never duplicate the axis.
            band_top = top - 45
            canvas.setFillColor(colors.HexColor("#edf8f1"))
            canvas.roundRect(left, band_top - 38, content_width, 33, 9, stroke=0, fill=1)
            canvas.setFillColor(colors.HexColor("#147d52"))
            cells = (str(toric["model"]), fmt(toric["spherical_equivalent_iol_d"]) + " D", fmt(toric["marker_axis_deg"], 1) + "°")
            for idx, label in enumerate(cells):
                canvas.setFont("IOL-Bold", 14)
                canvas.drawCentredString(left + content_width * (idx + .5) / 3, band_top - 26, label)
            canvas.setStrokeColor(colors.HexColor("#bdd6c9"))
            for idx in (1, 2):
                xx = left + content_width * idx / 3
                canvas.line(xx, band_top - 32, xx, band_top - 11)
        values.drawOn(canvas, left, top-(91 if toric else 27)-values_height)
        bio.drawOn(canvas, left, top-(100 if toric else 36)-values_height-bio_height)
        diagram_top = top-(110 if toric else 46)-values_height-bio_height
        draw_eye(canvas, item.eye, width/2, diagram_top, toric["marker_axis_deg"] if toric else None, tr, diagram_radius)
        if warning:
            warning_y = diagram_top-diagram_height-warning_height-12
            canvas.setFillColor(colors.HexColor("#fff3da"))
            canvas.rect(left, warning_y-5, content_width, warning_height+10, stroke=0, fill=1)
            warning.drawOn(canvas, left+7, warning_y)
        footer = paragraph(tr("Dashed line: toric marker axis. No line when no toric axis is available.\nDecision support only. Final responsibility rests with the surgeon. Verify patient, eye, lens and axis before surgery.",
                              "Kesikli çizgi: torik işaret aksı. Torik aks yoksa çizgi gösterilmez.\nKarar desteğidir. Nihai sorumluluk cerrahtadır. Cerrahi öncesi hasta, göz, lens ve aksı doğrulayın."), 7.5)
        footer.wrap(content_width, 55); footer.drawOn(canvas, left, 27)
        canvas.setFillColor(colors.HexColor("#34495e"))
        canvas.setFont("IOL-Regular", 5.8)
        canvas.drawString(left, 16, f"Software: {versions.get('software') or 'UNKNOWN'} | IOL policy: {versions.get('clinical_policy') or 'UNKNOWN'}")
        canvas.drawString(left, 8, f"Commit: {versions.get('deployment_sha') or 'UNKNOWN'}")
        canvas.showPage()
    canvas.save()
    return buffer.getvalue()
