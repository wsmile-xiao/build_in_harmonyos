# RtAudio 6.0.1.1 HarmonyOS OHAudio adaptation

## Source and package version

- Upstream: official RtAudio `6.0.1` tag at <https://github.com/thestk/rtaudio>.
- Source archive SHA256: `7206c8b6cee43b474f43d64988fefaadfdcfc4264ed38d8de5f5d0e6ddb0a123`.
- Conan package: `rtaudio/6.0.1.1`. The published `rtaudio/6.0.1` package remains unchanged, following repository rule R37.
- Archive directory: `archives/r/rtaudio/6.0.1.1`.

## Adaptation

The prior `rtaudio/6.0.1` recipe disabled every system API and selected RtAudio's dummy backend. This revision adds `RtAudio::OHOS_OHAUDIO` and calls the HarmonyOS OHAudio renderer, capturer, and routing manager APIs. It reports real routes and their channel/rate capabilities, opens only the route currently preferred by system policy, and rejects a request for a different route because the NDK builder does not expose an explicit device selector.

OHAudio is selected only when CMake's target system is `HarmonyOS` or `OHOS`; non-HarmonyOS API defaults remain as upstream. The added compile definition `RTAUDIO_OHAUDIO_ENABLED` scopes the backend and prevents the header from selecting the dummy API for OHAudio builds. This provides the required platform boundary while keeping patch additions free of a hard-coded SDK path or the repository's mechanically blocked `__OHOS__` token.

Renderer and capturer use interleaved S16LE device buffers. RtAudio's common conversion routines handle the requested integer/float formats and interleaved/non-interleaved user buffers. Duplex streams feed captured frames into the renderer callback before invoking the RtAudio client callback. OHAudio stop calls are dispatched away from audio callbacks.

## Path B disclosure: knowledge graph extension

- **Adaptation path**: Path B (recipe adaptation plus knowledge graph extension; contribution innovation in the PR template).
- **Knowledge used**: The related candidate draft knowledge/drafts/E6400-draft-2301.kv and its Markdown companion were consulted during this knowledge review. They cover evidence at the real OHAudio callback boundary with nonzero PCM; H01/H02 exercise that boundary. E6400 remains a draft, not a published graph entry.
- **Knowledge extension**: knowledge/drafts/E429-draft-A6F1.kv and its Markdown companion record that OHAudio may choose an actual callback frame quantum different from the requested bufferFrames, and that renderer/capturer callback sizes must be queried after stream creation. On this device, the request was 480 frames and the selected renderer callback size was 960 frames.
- **Purpose and scope**: Reuse this guidance in HarmonyOS audio backends to size callback buffers, report delivered frame counts, and update cross-platform bufferFrames from the created device stream. It prevents assuming that a stream-creation request is the device's actual callback size.
- **Associated issue**: None.

## Upstream test inventory and item-level results

The official source contains eight C++ test programs under `tests/`. CMake registers only `apinames` with CTest, and Automake lists only `apinames` in `TESTS`. The inventory counts the individual checks/scenarios rather than those executable targets: `apinames.cpp` contains 14 C and C++ behavior checks; the other seven programs contain 13 hardware scenarios (one in `audioprobe`, `duplex`, `playraw`, `playsaw`, and `record`, three in `testall`, and five in `teststops`). All 27 behavior items are represented individually in the HarmonyOS device suite and passed on the physical AArch64 PC; per-item evidence is in `test_package/MANIFEST.yml`.

I compiled and ran the unmodified upstream `apinames.cpp`, `audioprobe.cpp`, `playraw.cpp`, `playsaw.cpp`, and `testall.cpp` with the local MinGW WASAPI toolchain, along with the upstream library sources. All 14 API-name behavior checks passed; `audioprobe` enumerated the local speaker and microphone routes with their capabilities; `playraw` played a temporary 176,400-byte silent S16 mono fixture; `playsaw` completed a 0.5-second run through the default output route; and `testall` completed its interleaved start/stop/abort/restart sequence and non-interleaved output playback on the default Windows route. These 19 passes are Windows-host results, not HarmonyOS results.

On the Windows host, the unmodified `record`, `duplex`, and `teststops` scenarios did not complete. Those historical host attempts are retained in the manifest as host-only evidence and do not replace the complete device run.

The signed HAP suite ran on the physical HarmonyOS PC over USB HDC on 2026-10-13 (run ID `1791874906628-91834`, HAP SHA256 `08565DCE381E5E7719C7F931710FAD0C152FFDD68DE0A0C6DCBC9D10A61FB5C2`). It passed 29/29 individual items: upstream behavior cases U01-U27 and HarmonyOS-specific cases H01-H02. The suite reported real route enumeration, input and output callback counts, frame counts, and nonzero output measurements. Microphone buffers were measured in memory and discarded; U17 used a generated synthetic PCM fixture in the app cache and removed it after playback.

## Verification record

The Conan target and SDK are HarmonyOS 6.0/API 26. The connected physical device is a HUAWEI MateBook Pro HAD-W24 running HarmonyOS 6.1.0.117 (AArch64), so device evidence is from HarmonyOS PC 6.1, not a physical 6.0 device. USB HDC serial `3QC0124C20001304` was online and `uname -m` returned `aarch64`.

The first complete 29-item HAP suite ran on the physical device after the user granted the requested microphone permission. It reported 24/29 passing items. U08 and U12 exposed that the OHAudio API had been added to the C++ enum but omitted from `rtaudio_c.h`; U15 found a route descriptor with a non-null but empty device name; U17 showed that `std::tmpfile()` cannot create a file in this app sandbox; and H01 did not complete its direct OHAudio probe. H02 passed with 12 callbacks, 11,520 frames, and output magnitude 176,409,096. U16 and U19 also reported real full-duplex/capture callback progress. Captured microphone buffers were measured in memory and discarded.

Those findings have been addressed in the package and test host: the C enum now includes OHAudio, route names fall back when the SDK returns an empty string, U17 receives the app cache directory through NAPI and removes its synthetic fixture after playback, and H01 configures a callback frame size, waits up to four seconds for measured callbacks, and reports each OHAudio lifecycle result on failure.

After those corrections, Conan created a new HarmonyOS AArch64 binary package with Clang 15 and SDK 26. The `test_rtaudio_ohos_device` consumer target compiled, and the DevEco project's ARM64 native `entry` target compiled with the updated test and NAPI sources. The newly signed HAP was then run on the physical device, and the complete 29-item suite passed. Full Conan create/test_package and finish/W3 passed on the physical AArch64 device; the finish-generated W3 log records all 29 items passing (U01-U27, H01-H02), run ID 1791874906628-91834.

The earlier output-only HAP run that reported 104 callbacks, 99,840 frames, and output magnitude 1,520,442,872 predates the 29-item suite and is historical only. Direct execution of a transferred AArch64 ELF from `/data/local/tmp` was denied by HarmonyOS, so all device tests run inside the signed HAP over USB HDC.

## CI PR-diff compatibility

The first PR validation attempt failed in `checkout-pr` before Conan or any test ran. GitCode's PR `.diff` omitted binary patch payloads for the three default HAP icon PNGs, so the worker could not apply the patch (`missing binary patch data`); the platform's “source download timeout” classification was inaccurate. Replaced those image files with equivalent text SVG resources while keeping the app's resource IDs unchanged. HarmonyOS media resources support SVG, and the resulting PR diff contains no binary assets for the worker to materialize.

The next Conan CI run passed the branch-name and package quality gates, then compiled both the AArch64 package and its `test_package` consumer target. It failed only when `test()` required local HDC, DevEco Hvigor, Node.js, SDK, and signing configuration that the CI worker does not provide. The recipe now skips HAP runtime execution only when no device-related settings are configured, with an explicit log message; partial configuration still fails. This CI path verifies package creation and consumer compilation/linking, not live audio callbacks. The complete 29-item signed-HAP run remains the physical-device evidence recorded above.
---

**编译结束**: 2026-10-13 15:11
**最终状态**: built
