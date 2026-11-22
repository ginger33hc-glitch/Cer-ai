# CER-AI mobile validation app

Android and iOS share a React Native WebView application. This is source code for a validation build, not an installed/released phone app. Device testing, signed native builds and distribution are still required.

The CER-AI login and IOL workflow load at `https://cer-ai.com/iol`. A completed plan uses the existing canonical payload builder. The native bridge accepts requests only from the top-level CER-AI IOL page. ESCRS opens in a separate ephemeral WebView; the same canonical DOM adapter as the desktop helper fills and reads back values. Toric is enabled independently per eye. No formula or clinical recommendation is reimplemented in this app.

The full patient name is excluded by the web payload builder. The transfer is held in memory, is never embedded in a URL or a persistent native store, and expires after ten minutes. Returning to CER-AI destroys the ESCRS WebView. The CER-AI WebView keeps its own authenticated web session; the app does not read passwords or session cookies. Background screens are covered. No patient data is sent to Expo by the native application code.

Only currently verified exact lens mappings are supported. Previous refractive surgery remains unsupported. ESCRS terms must be reviewed by the user; the app never accepts them or presses Calculate. Predicted ESCRS PCA and formula-specific constants still need review. PDF/share flows, image upload, camera/gallery permission flows, login persistence and ESCRS DOM filling require device acceptance tests.

## Development

From `mobile`:

```sh
npm ci
npm run sync-adapter
npm test
npx expo install --check
npx expo export --platform all
```

`src/adapter-source.js` is a generated string of `extensions/escrs-assistant/adapter.js`. Edit only the canonical adapter, regenerate, and run tests; do not fork the clinical field mapping.

`npx expo start` can serve a local development session for compatible Expo Go or a development client. A reachable development host is required; this is not production distribution.

## Native builds and distribution

The identifiers `com.cerai.mobile` are provisional until availability/ownership is verified. No Apple team, Expo project ID, signing key or credentials are invented or committed.

With the owner's authenticated Expo account, initialize/link the project using EAS, then:

```sh
npx eas-cli build --platform android --profile preview
npx eas-cli build --platform ios --profile simulator
npx eas-cli build --platform ios --profile preview
```

The Android preview produces an installable APK. The iOS simulator profile is not installable on a physical iPhone. A physical iPhone preview requires appropriate Apple signing/provisioning and registered test devices, or a TestFlight distribution build. Store release also requires developer accounts and store review. Do not claim a phone release from a JavaScript bundle export.

## Acceptance before calling the mobile feature verified

1. Sign in, select images, complete a synthetic bilateral plan.
2. OD PanOptix Toric and OS PureSee non-toric: confirm OD Toric checked, OS unchecked; identities, all biometry, exact lenses, targets, SIA and incision match.
3. Reverse the two eye types, test unilateral transfer and missing LT.
4. Complete an ESCRS terms prompt manually and retry without reentering measurements.
5. Test slow network/reload, wrong model, invalid values and navigation away; no false success or data leakage.
6. Close ESCRS, confirm CER-AI plan remains available; verify expiry and background display behavior.
7. Repeat on a physical Android phone and an iPhone. No real patient data is needed.
