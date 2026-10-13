"""Manufacturer model/cylinder specifications, reviewed 2026-10-13.

Powers are at the IOL plane. These data do not validate the optical prototype,
assert local stock/regulatory availability, or substitute for the product IFU.
Display labels containing CYL are model plus cylinder, never invented SKUs.
"""

VERIFIED_LENS_STEPS: dict[str, dict[str, float]] = {
    "clareon-toric-cnw0t8": {
        "CNW0T2": 1.00, "CNW0T3": 1.50, "CNW0T4": 2.25, "CNW0T5": 3.00,
        "CNW0T6": 3.75, "CNW0T7": 4.50, "CNW0T8": 5.25, "CNW0T9": 6.00,
    },
    "clareon-panoptix-toric-cnwtt3": {
        "CNWTT2": 1.00, "CNWTT3": 1.50, "CNWTT4": 2.25,
        "CNWTT5": 3.00, "CNWTT6": 3.75,
    },
    "clareon-vivity-toric-cnwet2": {
        "CNWET3": 1.50, "CNWET4": 2.25, "CNWET5": 3.00,
        "CNWET6": 3.75, "CNWET7": 4.50, "CNWET8": 5.25, "CNWET9": 6.00,
    },
    "tecnis-mono-toric-zct375": {
        "ZCT100": 1.00, "ZCT150": 1.50, "ZCT225": 2.25, "ZCT300": 3.00,
        "ZCT375": 3.75, "ZCT450": 4.50, "ZCT525": 5.25, "ZCT600": 6.00,
        "ZCT700": 7.00, "ZCT800": 8.00,
    },
    "tecnis-eyhance-toric-diu525": {
        "DIU100": 1.00, "DIU150": 1.50, "DIU225": 2.25,
        "DIU300": 3.00, "DIU375": 3.75, "DIU450": 4.50, "DIU525": 5.25,
    },
    "tecnis-odyssey-toric-drt150": {
        "DRT150": 1.50, "DRT225": 2.25, "DRT300": 3.00, "DRT375": 3.75,
    },
    "tecnis-puresee-toric-det150": {
        "DET100": 1.00, "DET150": 1.50, "DET225": 2.25, "DET300": 3.00,
        "DET375": 3.75, "DET450": 4.50, "DET525": 5.25, "DET600": 6.00,
    },
    "eyecryl-toric-hfy20": {
        "HFY-05": 1.00, "HFY-10": 1.50, "HFY-20": 2.25, "HFY-30": 3.00,
        "HFY-35": 3.75, "HFY-40": 4.50, "HFY-50": 5.25, "HFY-60": 6.00,
    },
    "eyecryl-actv-toric-hfyd20": {
        "HFYD-05": 1.00, "HFYD-10": 1.50, "HFYD-20": 2.25, "HFYD-30": 3.00,
        "HFYD-35": 3.75, "HFYD-40": 4.50, "HFYD-50": 5.25, "HFYD-60": 6.00,
    },
    "enova-advance-toric": {
        "PAD3": 1.50, "PAD4": 2.25, "PAD5": 3.00, "PAD6": 3.75,
    },
    "liberty-trifocal-toric": {
        f"677MT/677MTY / CYL {c:.2f} D": c
        for c in (1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00, 4.50, 5.25, 6.00)
    },
    "elon-toric-bi-flex": {
        "877PETY T2": 1.00, "877PETY T3": 1.50, "877PETY T4": 2.25,
        "877PETY T5": 3.00, "877PETY T6": 3.75, "877PETY T7": 4.50,
        "877PETY T8": 5.25, "877PETY T9": 6.00,
    },
    "rayone-emv-toric": {
        f"RAO210T / CYL {c:.2f} D": c for c in (0.75, 1.50, 2.25, 3.00, 3.75, 4.50)
    },
    "rayone-trifocal-toric": {
        f"RAO613Z / CYL {c:.2f} D": c for c in (0.75, 1.50, 2.25, 3.00, 3.75, 4.50)
    },
}

TORIC_SOURCES = {
    "clareon-toric-cnw0t8": ["https://www.accessdata.fda.gov/cdrh_docs/pdf19/P190018B.pdf", "https://www.info.pmda.go.jp/downfiles/md/PDF/400487/400487_30200BZX00290000_A_01_04.pdf"],
    "clareon-panoptix-toric-cnwtt3": ["https://www.legislation.gov.au/F2026L00773/asmade/2026-06-22/text/original/epub/OEBPS/document_2/document_2.html"],
    "clareon-vivity-toric-cnwet2": [
        "https://alcon.widen.net/s/7j6jfmhlns/clareon-vivity-spec-sheet-blf---november-new-bigs_us-viv-2200069",
        "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?ID=P190018S046",
    ],
    "tecnis-mono-toric-zct375": ["https://catalog.emeaassets.com/productsen/?page_id=1284"],
    "tecnis-eyhance-toric-diu525": ["https://catalog.emeaassets.com/productsen/?page_id=1329"],
    "tecnis-odyssey-toric-drt150": ["https://www.opc.hu/documents/TECNIS_Odyssey_IOL_Spec_Sheets_2024.pdf"],
    "tecnis-puresee-toric-det150": ["https://catalog.emeaassets.com/productsen/?page_id=6999"],
    "eyecryl-toric-hfy20": ["https://biotechhealthcare.com/products/eyecryl-toric/"],
    "eyecryl-actv-toric-hfyd20": ["https://biotechhealthcare.com/products/eyecryl-actv-toric/"],
    "enova-advance-toric": ["https://www.vsybiotechnology.com/downloads/enova-advanced-brochure.pdf"],
    "liberty-trifocal-toric": ["https://medicontur.com/professionals/products/intraocular-lenses/toric/liberty-toric"],
    "elon-toric-bi-flex": ["https://medicontur.com/professionals/products/intraocular-lenses/edof/bi-flex-elon-pob-ma-toric"],
    "rayone-emv-toric": ["https://rayner.com/global/en/iol/monofocal/rayone-emv-toric/"],
    "rayone-trifocal-toric": ["https://rayner.com/global/en/iol/trifocal/rayone-trifocal-toric/", "https://rayner.com/global/wp-content/uploads/sites/21/2021/11/RAY04662_Rayner-Premium-IOL-Brochure-EN-0422.pdf"],
}

TORIC_NOTES = {
    "enova-advance-toric": "PAD2 1.00 D is marked available soon in the August 2025 brochure and is excluded. The clinic label TPADC 375 is not a verified manufacturer model alias; results use PAD identifiers.",
    "clareon-toric-cnw0t8": "CNW0T2 1.00 D is documented in the Japanese PMDA labeling; local availability must be confirmed.",
    "clareon-vivity-toric-cnwet2": "CNWET2 is not in the reviewed model/power table and is excluded. CNWET7-9 are supported by the 2026 FDA extension; local availability is unverified.",
    "rayone-emv-toric": "One model with multiple cylinder powers; CYL labels are display descriptors, not separate manufacturer model codes.",
    "rayone-trifocal-toric": "One model with multiple cylinder powers; CYL labels are display descriptors, not separate manufacturer model codes.",
    "liberty-trifocal-toric": "677MT and 677MTY share the listed powers. Confirm the clear/yellow variant and cylinder when ordering.",
}

# Documented spherical-equivalent ranges for newly enabled families. Existing
# clinic A-constants are retained; they are independent of cylinder powers.
TORIC_SPHERE_BOUNDS = {
    "tecnis-mono-toric-zct375": (5.0, 34.0),
    "tecnis-odyssey-toric-drt150": (5.0, 34.0),
    "tecnis-puresee-toric-det150": (5.0, 34.0),
    "eyecryl-toric-hfy20": (10.0, 30.0),
    "eyecryl-actv-toric-hfyd20": (10.0, 30.0),
    "enova-advance-toric": (10.0, 30.0),
    "liberty-trifocal-toric": (8.0, 30.0),
    "elon-toric-bi-flex": (10.0, 30.0),
    "rayone-emv-toric": (10.0, 25.0),
    "rayone-trifocal-toric": (6.0, 30.0),
}

# Audit/display values are derived from the same table used by the prototype.
MANUFACTURER_TORIC_REFERENCES = {
    lens_id: {
        "models": list(steps), "cylinder_iol_plane_d": list(steps.values()),
        "source": TORIC_SOURCES[lens_id][0], "sources": TORIC_SOURCES[lens_id],
        "note": TORIC_NOTES.get(lens_id, "Confirm regional availability and the product IFU."),
        "reviewed_on": "2026-10-13", "clinical_calculation_authorized": False,
    }
    for lens_id, steps in VERIFIED_LENS_STEPS.items()
}
