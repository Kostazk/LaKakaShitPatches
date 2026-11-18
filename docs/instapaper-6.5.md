# Instapaper 6.5: AI speech investigation

The reported failure is selecting an AI voice and seeing:
"Couldn't load speech from the server. Try again later."

## Findings

- Tested the supplied Instapaper 6.5 APK, version code 189, against the upstream
  1.3.1 bundle using Morphe Desktop 2.2.0 / patcher 2.4.0. The existing premium
  getter fingerprint matches and the patched APK rebuilds successfully.
- The getter is `Lkc/d0;->I()Ljava/lang/String;` in this build. Its derived
  boolean check `V()Z` interprets any value other than `"0"` as active.
- AI speech is fetched through a separate `POST /api/tts/speech` request.
  Changing the local preference getter cannot grant an entitlement on that server.
- `SpeechRemoteSource` classifies HTTP 401/403 as authentication/access errors,
  429 as rate limiting, and 500–599 as server errors.
- The resource error mapper `Lyb/a;->c(Resources, Throwable)` replaces all
  `SpeechRemoteSourceException` messages with the same generic text. Invalid
  received/cached audio also maps to that text. The text alone does not prove
  that a request received HTTP 403 or that the account lacks a subscription.
- Instapaper describes AI Voices as a Premium feature:
  https://www.instapaper.com/premium
  https://blog.instapaper.com/2026/07/28/instapaper-10/

## Changes in this fork

1. Stop swallowing exceptions in the existing local premium patch.
2. Describe its scope accurately; it does not provide server-side AI audio.
3. Include **Show AI speech error details** automatically with **Unlock Premium**.
   Version 1.3.3 uses the same app compatibility as the premium patch and checks
   for the matching speech API before changing code. Builds without that API
   keep their original error handling. Version 6.5 is tested.
   It exposes the HTTP status already present in the exception, or identifies
   an invalid audio file. It does not display response bodies, request text,
   cookies, tokens, account data, or other credentials.
4. Update the Gradle plugin and patcher to the current official template's
   2.1.1 / 2.4.0 versions. Include a public-tool portable build route.

## Selection fix in v1.3.3

Version 1.3.2 declared diagnostics as a separate default-disabled patch with an
exact version restriction. Expert mode alone did not resolve selection on the
affected phone. Version 1.3.3 removes that separate-selection requirement.

## Trying the diagnostic bundle

Import `patches-1.3.3.mpp` into a current Morphe Manager, or add:
https://morphe.software/add-source?github=Kostazk/LaKakaShitPatches

Select the original, unpatched Instapaper 6.5 APK and enable **Unlock Premium**.
The diagnostic patch is a dependency and runs automatically, even if Manager
shows only the premium checkbox. Expert mode is not required.

Patch and install using the same signing key as your current patched app.
Selecting the AI voice again should reveal a more specific error. If Android
refuses an update due to a different signing key, do not uninstall your current
app without first securing any unsynced data.

| Diagnostic result | Meaning / next check |
| --- | --- |
| HTTP 401 | Authentication failed; check the signed-in session. |
| HTTP 403 | The server refused access. Account entitlement is one possible cause; this code alone does not identify the server's reason. |
| HTTP 429 | The server is rate limiting requests. |
| HTTP 500–599 | A server error; a local preference change cannot repair the server. |
| No HTTP status | A speech request failed without a status in its exception. |
| Invalid audio | The received or cached audio failed validation. |

No live request from the affected phone/account has been captured. This release
is diagnostic; successful phone playback has not been verified and is not promised.
Other apps in the inherited bundle have not been tested in this investigation.

## Building

The standard project build requires access to Morphe's GitHub Packages registry.
An alternative using pinned, SHA-256 checked public tool releases is:

```sh
python tools/build_portable.py --java /path/to/java21/bin/java --jdk /path/to/jdk21
```

The result includes both JVM classes and Android `classes.dex`, along with the
original GPL extension and utility classes. It is written to
`patches/build/libs/patches-1.3.3.mpp`. Java 21 or newer is needed for the tools;
the patch's own JVM bytecode target remains 11 and Android DEX minimum API is 26.

## Validation

- Kotlin compilation and Android D8 compilation completed successfully.
- With only **Unlock Premium** explicitly selected, both patches ran on the
  supplied 6.5 APK under strict `--validate` checks. Rebuilding succeeded and
  disassembly confirmed the diagnostic messages in the error mapper, so
  diagnostics did not skip this APK.
- The modified DEX was disassembled to check the local getter and diagnostic
  branches. No application installation or live account test was performed.
