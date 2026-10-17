# Browserbase ESCRS handoff (release candidate)

Status: implemented and tested with simulated provider responses; live account setup
and anonymous end-to-end validation are still required. Production must remain on
Browserless until these gates pass. No subscription purchase is required for the
initial Free plan trial.

## Configuration

- `CERAI_ESCRS_PROVIDER=browserbase` selects the new provider explicitly.
- `BROWSERBASE_API_KEY` is a server-side secret. Never commit it or return it to clients.
- `BROWSERBASE_PROJECT_ID` optionally selects the project; otherwise the provider
  infers it from the key. No patient identifiers appear in provider metadata.
- No automatic fallback sends a case to a provider the surgeon did not authorize.

The browser lifetime is 425 seconds: up to 125 seconds for preparation and 300
seconds after verified readback. Free-plan sessions cannot use paid keepAlive;
CER-AI holds its CDP connection for the bounded viewer window instead. The worker
closes the connection and requests release after End session, timeout or failure.
The provider's absolute timeout remains the cleanup backstop if release fails.
Two active sessions maximum and one per signed-in user are allowed.

## Data and consent

Use the existing canonical adapter and exact per-eye lens mapping. Read back the
selected model for every loaded eye before issuing a viewer link. Do not calculate
or substitute a lens automatically. The provider-specific confirmation names
Browserbase and ESCRS and lists transmitted fields. Browserless-only legacy consent
cannot authorize Browserbase. Persist the consent audit before contacting either
provider; audit outcomes contain no measurements, initials, credentials or viewer
URLs.

Source images and full patient names are not sent. Request session recording,
provider logs and automatic CAPTCHA solving disabled. No persisted browser profile
is used. These API options do not by themselves establish any wider retention or
regulatory guarantee.

## Mobile and isolation

Browserbase documents that mobile native keyboards are not officially supported.
The authenticated CER-AI viewer therefore provides a local text input and limited
keys forwarded only to an editable field on the ESCRS hostname. No arbitrary CDP
commands or keyboard chords are accepted. Requests are bounded and user-scoped;
other users cannot view, type into or close a session. Viewer assets are versioned
by content hash. The Browserbase iframe is permitted only on the session route;
other CSP and authentication restrictions remain in force.

## Before activation

1. Complete Browserbase Free account setup and provision its server-side key.
2. Run a wholly synthetic bilateral toric/non-toric case. Verify exact model,
   manufacturer, toric mode, target, incision, SIA and biometry in both eyes.
3. Verify phone touch selection, local text entry and tab/enter controls.
4. Keep the viewer open for five minutes, then verify automatic termination and
   release. Confirm End session closes it early and owner isolation remains intact.
5. Check quota and actual consumption: the advertised Free allowance is one browser
   hour per month with up to 15 minutes per session. Preparation consumes time too.
6. Activate the provider only after these checks; do not claim live success from mocks.

Official references checked 17 October 2026:
- https://www.browserbase.com/pricing
- https://docs.browserbase.com/platform/browser/observability/session-live-view
- https://docs.browserbase.com/reference/api/create-a-session
