# Toric catalog review — 2026-10-13

Scope: all 14 toric families in the 30-entry clinic catalog. Manufacturer cylinder specifications support the existing TEST_ONLY optical prototype; no claim of clinical validation or local availability is made. Non-toric entries are not silently substituted with another implant. Existing clinic A-constants are unchanged.

The canonical values and provenance live in `iol_module/toric_catalog.py`; API references are derived from them. All powers below are at the IOL plane.

| Lens family | Model / cylinder definitions | Primary evidence |
|---|---|---|
| CLAREON Mono Toric (CNW0T series) | CNW0T2: 1.00 D; CNW0T3: 1.50 D; CNW0T4: 2.25 D; CNW0T5: 3.00 D; CNW0T6: 3.75 D; CNW0T7: 4.50 D; CNW0T8: 5.25 D; CNW0T9: 6.00 D | [Source 1](https://www.accessdata.fda.gov/cdrh_docs/pdf19/P190018B.pdf); [Source 2](https://www.info.pmda.go.jp/downfiles/md/PDF/400487/400487_30200BZX00290000_A_01_04.pdf) |
| CLAREON PanOptix Toric (CNWTT2) | CNWTT2: 1.00 D; CNWTT3: 1.50 D; CNWTT4: 2.25 D; CNWTT5: 3.00 D; CNWTT6: 3.75 D | [Source 1](https://www.legislation.gov.au/F2026L00773/asmade/2026-06-22/text/original/epub/OEBPS/document_2/document_2.html) |
| CLAREON Vivity Toric (CNWET series) | CNWET3: 1.50 D; CNWET4: 2.25 D; CNWET5: 3.00 D; CNWET6: 3.75 D; CNWET7: 4.50 D; CNWET8: 5.25 D; CNWET9: 6.00 D | [Source 1](https://alcon.widen.net/s/7j6jfmhlns/clareon-vivity-spec-sheet-blf---november-new-bigs_us-viv-2200069); [Source 2](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?ID=P190018S046) |
| TECNIS Mono Toric (ZCT375) | ZCT100: 1.00 D; ZCT150: 1.50 D; ZCT225: 2.25 D; ZCT300: 3.00 D; ZCT375: 3.75 D; ZCT450: 4.50 D; ZCT525: 5.25 D; ZCT600: 6.00 D; ZCT700: 7.00 D; ZCT800: 8.00 D | [Source 1](https://catalog.emeaassets.com/productsen/?page_id=1284) |
| TECNIS Eyhance Toric (DIU525) | DIU100: 1.00 D; DIU150: 1.50 D; DIU225: 2.25 D; DIU300: 3.00 D; DIU375: 3.75 D; DIU450: 4.50 D; DIU525: 5.25 D | [Source 1](https://catalog.emeaassets.com/productsen/?page_id=1329) |
| TECNIS Odyssey Toric (DRT150) | DRT150: 1.50 D; DRT225: 2.25 D; DRT300: 3.00 D; DRT375: 3.75 D | [Source 1](https://www.opc.hu/documents/TECNIS_Odyssey_IOL_Spec_Sheets_2024.pdf) |
| TECNIS PureSee Toric (DET150) | DET100: 1.00 D; DET150: 1.50 D; DET225: 2.25 D; DET300: 3.00 D; DET375: 3.75 D; DET450: 4.50 D; DET525: 5.25 D; DET600: 6.00 D | [Source 1](https://catalog.emeaassets.com/productsen/?page_id=6999) |
| EYECRYL Toric (HFY20) | HFY-05: 1.00 D; HFY-10: 1.50 D; HFY-20: 2.25 D; HFY-30: 3.00 D; HFY-35: 3.75 D; HFY-40: 4.50 D; HFY-50: 5.25 D; HFY-60: 6.00 D | [Source 1](https://biotechhealthcare.com/products/eyecryl-toric/) |
| EYECRYL ACTV Toric (HFYD20) | HFYD-05: 1.00 D; HFYD-10: 1.50 D; HFYD-20: 2.25 D; HFYD-30: 3.00 D; HFYD-35: 3.75 D; HFYD-40: 4.50 D; HFYD-50: 5.25 D; HFYD-60: 6.00 D | [Source 1](https://biotechhealthcare.com/products/eyecryl-actv-toric/) |
| ENOVA Advanced Toric (PAD series) | PAD3: 1.50 D; PAD4: 2.25 D; PAD5: 3.00 D; PAD6: 3.75 D | [Source 1](https://www.vsybiotechnology.com/downloads/enova-advanced-brochure.pdf) |
| LIBERTY Trifocal Toric | 677MT/677MTY / CYL 1.00 D: 1.00 D; 677MT/677MTY / CYL 1.50 D: 1.50 D; 677MT/677MTY / CYL 2.00 D: 2.00 D; 677MT/677MTY / CYL 2.50 D: 2.50 D; 677MT/677MTY / CYL 3.00 D: 3.00 D; 677MT/677MTY / CYL 3.50 D: 3.50 D; 677MT/677MTY / CYL 4.00 D: 4.00 D; 677MT/677MTY / CYL 4.50 D: 4.50 D; 677MT/677MTY / CYL 5.25 D: 5.25 D; 677MT/677MTY / CYL 6.00 D: 6.00 D | [Source 1](https://medicontur.com/professionals/products/intraocular-lenses/toric/liberty-toric) |
| ELON Toric (Bi-Flex) | 877PETY T2: 1.00 D; 877PETY T3: 1.50 D; 877PETY T4: 2.25 D; 877PETY T5: 3.00 D; 877PETY T6: 3.75 D; 877PETY T7: 4.50 D; 877PETY T8: 5.25 D; 877PETY T9: 6.00 D | [Source 1](https://medicontur.com/professionals/products/intraocular-lenses/edof/bi-flex-elon-pob-ma-toric) |
| RayOne EMV Toric | RAO210T / CYL 0.75 D: 0.75 D; RAO210T / CYL 1.50 D: 1.50 D; RAO210T / CYL 2.25 D: 2.25 D; RAO210T / CYL 3.00 D: 3.00 D; RAO210T / CYL 3.75 D: 3.75 D; RAO210T / CYL 4.50 D: 4.50 D | [Source 1](https://rayner.com/global/en/iol/monofocal/rayone-emv-toric/) |
| RayOne Trifocal Toric | RAO613Z / CYL 0.75 D: 0.75 D; RAO613Z / CYL 1.50 D: 1.50 D; RAO613Z / CYL 2.25 D: 2.25 D; RAO613Z / CYL 3.00 D: 3.00 D; RAO613Z / CYL 3.75 D: 3.75 D; RAO613Z / CYL 4.50 D: 4.50 D | [Source 1](https://rayner.com/global/en/iol/trifocal/rayone-trifocal-toric/); [Source 2](https://rayner.com/global/wp-content/uploads/sites/21/2021/11/RAY04662_Rayner-Premium-IOL-Brochure-EN-0422.pdf) |

## Deliberate limits

- ENOVA Advanced Toric (PAD series): PAD2 1.00 D is marked available soon in the August 2025 brochure and is excluded. The clinic label TPADC 375 is not a verified manufacturer model alias; results use PAD identifiers.
- CLAREON Mono Toric (CNW0T series): CNW0T2 1.00 D is documented in the Japanese PMDA labeling; local availability must be confirmed.
- CLAREON Vivity Toric (CNWET series): CNWET2 is not in the reviewed model/power table and is excluded. CNWET7-9 are supported by the 2026 FDA extension; local availability is unverified.
- RayOne EMV Toric: One model with multiple cylinder powers; CYL labels are display descriptors, not separate manufacturer model codes.
- RayOne Trifocal Toric: One model with multiple cylinder powers; CYL labels are display descriptors, not separate manufacturer model codes.
- LIBERTY Trifocal Toric: 677MT and 677MTY share the listed powers. Confirm the clear/yellow variant and cylinder when ordering.

The Enova clinic label was changed to the documented PAD family rather than assuming that TPADC 375 is a validated alias. Rayner descriptors include cylinder because multiple powers share the same model code. RAO613Z spelling is supported by the Rayner premium brochure; the product webpage renders the letter O as zero in its model row.

Newly enabled families with documented spherical ranges reject an out-of-range spherical result rather than inventing an orderable lens. RayOne EMV Toric specifically rejects 27 D against its documented 10–25 D range.

Verification: each toric family exercises the application planning path with mocked K6 output, retaining TEST_ONLY status and ESCRS access. Source-specific tests protect Liberty half-diopter steps, Eyecryl codes, Rayner descriptors, the unavailable Enova PAD2 step, and the RayOne EMV spherical upper bound. The frontend test renders every model descriptor and verifies the previously mixed-language warning.
