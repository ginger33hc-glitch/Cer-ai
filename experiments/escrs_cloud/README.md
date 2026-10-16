# Browserless ESCRS synthetic prototype

Not a production feature. No installation on the viewer's phone; Chromium runs
in Browserless Cloud and its LiveURL is embedded in the viewer. The Browserless API token remains server-side.
The only supplied case is synthetic: OD PanOptix Toric, OS DEN00V non-toric.
The existing canonical adapter fills and reads back values; it does not submit
a calculation or accept terms. No arbitrary URL, JavaScript or patient-upload
endpoint is exposed. Tap and scroll support inspection; PDF download, automatic initial fill and recovery are not verified.

Configure BROWSERLESS_TOKEN in the server environment (never in source or chat).
Optional BROWSERLESS_HOST defaults to production-ams.browserless.io.
From repository root, in the existing development environment:

```sh
uvicorn experiments.escrs_cloud.server:app --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765, open ESCRS, review any terms yourself, and choose
**Fill test case**. A pass is reported only after the adapter's final read-back.
Disconnect or two minutes closes the browser. This developer harness has one
viewer slot and a same-origin cookie check, not production user authentication.
Do not expose it publicly or enter real patient information.

Before production: validate ESCRS form behavior, actual iPhone/Android viewing,
touch and download flows; add doctor/session authorization and isolated workers;
confirm ESCRS terms for the proposed service model (published clause 3.1).
No browser-session handoff into a separate ordinary ESCRS tab is claimed.

Validation status: BROWSERLESS_TOKEN was configured in Railway production on
2026-10-16. Browserless REST reached ESCRS with HTTP 200; BrowserQL created a
LiveURL. Standard /chromium/function lacks the LiveURL CDP command, so this
prototype uses the documented /chromium/stealth connection for hybrid sessions.
Full form render and the synthetic bilateral all-field read-back now PASS.
Real-device interaction and embedded-session continuity remain NOT VERIFIED.
Local Chromium installation is no longer required.

Observed account limit: 120,000 ms per session. A 300,000 ms LiveURL
request was rejected before launch; the prototype now uses 120 seconds.

Live validation notes (2026-10-17 Europe/Istanbul):
- Explicit owner confirmation permitted accepting the ESCRS terms for testing.
- Native BrowserQL click accepted the dialog; the form rendered.
- First full transfer failed at Gender: synthetic click did not open MudSelect.
- Actual Gender markup is a readonly input with role=combobox. MudSelect's
  upstream control opens via onmousedown. The canonical adapter now dispatches
  that event; its DOM contract and three adapter packaging tests pass.
- Patched full live read-back PASS: OD Clareon PanOptix Toric CNWTT2-6,
  OS DEN00V. The canonical adapter completed its final field-by-field checks,
  including Gender, manufacturer, Toric flags, both eyes' measurements and
  targets, surgeon/initials/age, OD incision 180 and SIA 0.25.
- Successful BrowserQL response had no errors and verify.value was
  {"OD":"Clareon PanOptix Toric CNWTT2-6","OS":"DEN00V"}.
- Seven focused Python checks plus the DOM contract scenarios passed.
