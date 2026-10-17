# QtBase 6.11.1.2 native test report

Final source: Qt Base 6.11.1 + 23 patches. OHOS armv8, HongMeng Kernel 1.12.0,
Clang 15.0.4, CMake 4.1.2, Conan 2.29.1. Current recipe and source provenance
are recorded in manifest.yaml and notes.md.

## Full upstream inventory

full76 built successfully and attempted all 532 configured CTest programs:
526 passed, 6 failed, zero timeouts and zero skipped programs. CTest exit 8;
serial execution, 900 seconds per program. Archive SHA256: `834bb063e44b315167639e674a63c9e21056370d8ce6691bde13dc599afb9cb7`.
Inventory, JUnit and untruncated LastTest.log have matching program names.

| Failed program | QtTest passed / failed / skipped | Observed boundary |
|---|---:|---|
| tst_qfile | 701 / 10 / 1 | XDG Trash, home, shared ownership and symlink fixtures |
| tst_qtemporaryfile | 60 / 1 / 0 | Same moveToTrash environment |
| tst_qpluginloader | 89 / 1 / 0 | Loading an ELF after removing section metadata |
| tst_qplugin | 11 / 1 / 0 | Modified signed plugin metadata, positive cbor-control |
| tst_qcollator | 23 / 2 / 57 | Numeric/punctuation options absent in POSIX backend without ICU |
| tst_qlocalsocket | 79 / 2 / 0 | Correct socket mode bits but native access(X_OK) returns EACCES |

All failures remain recorded. Private-storage trash and socket permission
probes are preserved in the external evidence package. The configuration
excludes OpenGL/GPU, XCB, fontconfig and ICU. No session bus means the QtDBus
suite is unregistered; its library remains enabled. QtTest rows and skips,
710 source registration sites and 846 source files are separate denominators.

## Final package

Official ConanVerifier G0/G1/G2/G3/G4/L2/L4/L5 and a fresh W3 build passed.
W3 ran 7 base and all 21 Wayland programs, then packaged and tested the ordinary
consumer. W3 log SHA256: `d866d93aa330d74a6076abe41888acf36a63e9b21a40e1de83a5a841aa04e756`.
Exact package: `qtbase/6.11.1.2#6987b9588536f153065fd7bbbe055d40:16b02108963dfa180909182973c9f449f0c4490e#377eefb9e2b783e8f4c1ddeff52e1fbc`.

Fresh consumer100 selected that exact package ID/revision and passed 44 mandatory
checks (9 CMake targets + 18 offscreen + 11 system + 4 codegen/shared-library
+ 2 expected-error exits) and 2 font checks. A separate copied-kit run passed
35 mandatory runtime + 2 font + 20 Wayland checks; process mappings verified
the loaded Qt/dependencies belonged to kit files. The Wayland server is Qt's
upstream mock compositor, not the OS desktop. Full KDE deployment is unverified.

All 40 recorded patched Qt source hashes match full76. The later recipe
change excludes upstream test fixtures from installation with Qt's existing
option; strict all-ELF architecture/signature checks remain enabled.

Local 23-patch replay, 19 recipe regressions and the real CMake install-scope
check passed. The native archive contains 5067 files and 94 ELF files;
SHA256 `33788add62fcf2034956865a71064671c8a6aa80215420f3ff8d4ad3e9f0560a`. Real qmake/qtpaths, runtime and archive verification
passed the follow-up official readiness check; the initial finish exit
1 remains preserved.

## Review and publication

See reports/audit-result.json for the independent unstaged-snapshot review.
The kit relocates absolute NEEDED entries to byte-matched bundled dependencies
and re-signs its private copies. needed-relocations.json records original and
delivered hashes; the original Conan cache and W3 package are preserved.
default111 also runs the delivered command with no kit environment overrides.
Its inherited HiShell TMPDIR is shared storage; the runner creates short
sockets in the native application directory and passes all runtime checks.

PF9's software-level metadata path conflict is retained; preflight is not all
green. C is a candidate requiring event acceptance of scope and exceptions.
Post-commit audit, public CI, task/version mapping and publication remain with
the participant. All raw diagnostic archives stay outside the source PR.


## CI #42411 timezone source correction

CI #42411 passed the L0 dependency, commands.json, directory and branch gates.
Conan create then stopped in probes/prepare_timezone.py because the helper
required a system tzdata2025b archive. The error check covered the header,
format and version together; the worker's actual tzdata version was not
printed. This failure was unrelated to PF9.

The corrected recipe obtains both tzdata2025b and tzcode2025b from IANA with
fixed SHA256 values and builds the upstream zic compiler using the configured
native C compiler. It no longer reads /system/etc/zoneinfo/tzdata. The helper
generates every default IANA zone, then materializes Link aliases as identical
regular files for the OHOS filesystem. Explicit application TZ behavior and
the package's TZDIR environment are unchanged.

Validation on the corrected helper:

- 598 generated TZif files: 341 canonical zones and 257 aliases. Every file
  matches independently built, unmodified upstream zic fed all original inputs.
- All 598 files parse with Python ZoneInfo; six known winter/summer offsets pass.
- Release mismatch, alias cycle, dangling alias and path traversal fail while
  preserving the previous output. Repeated generation removes stale entries.
- OHOS Clang 15 generation passes. All 598 target hashes match host reference.
- Existing native Qt consumer with the new TZDIR passes 11 system assertions.
- Complete native tst_qtimezone and tst_qdatetime both pass under the same
  TZ setting used by the recipe. An earlier ad-hoc run omitted that TZ setting
  and retained its systemZone failure; the recipe already supplies the setting.
- Actual Conan source() checks pass with all four pinned auxiliary archives;
  existing 19 recipe regression tests pass.

The earlier full76 526/532 result, W3 receipt and binary archive remain evidence
for their original recipe/runtime-data snapshot. This change does not modify
patched Qt C++ sources. A new CI run will establish the final whole-recipe
build/package result; no old receipt has been overwritten or marked as a new run.
# CI #42503 runtime-directory follow-up

This later CI compiled the complete product and selected test targets, then
passed 7/7 base programs and failed 20/21 Wayland programs. Nineteen failures
print bind() errno 1; the remaining reconnect failure also cannot create its
display. The sole pass intentionally tests a connection failure. The final
gate failure is upstream execution, not the bot's earlier network category.

An isolated target comparison ran the unchanged 21-program Wayland group:
the shared temporary parent failed, while /data/storage/el2/base/cache passed
all 21. A separate socket probe confirms shared bind errno 1, mode 02771 and
synthetic ownership despite chmod; the private cache gives owned mode 0700
and passes bind/listen/connect/accept plus data transfer.

The repaired recipe probes a fresh per-group directory and a nested Qt-style
socket path, selects the existing application cache on OHOS when required,
and scopes both TMPDIR and XDG_RUNTIME_DIR to each CTest invocation. All
candidate errors remain fatal if no directory works. Test selection,
assertions and timeouts are unchanged. Running this actual candidate group
method with a shared TMPDIR inherited at startup passes 7+21 programs and
verifies environment restoration and directory cleanup. Twenty host recipe
checks pass, including the failure paths. A fresh whole-recipe CI is pending.
The earlier W3/full76/native110 identities and 526/532 result remain distinct.
