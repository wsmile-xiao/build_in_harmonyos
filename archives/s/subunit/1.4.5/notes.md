# subunit 1.4.5 C binding — current review repair

The package ships only child.c/child.h and the dual license. Its source is the
unchanged official 1.4.5 tag archive, 105136 bytes, SHA-256
c55b39d0802ca15c18fbf267faf3a1cf67b4fe2482abbb00755c31b53c833bf7.
Python and C++ components are not packaged; this is not a waiver for C tests.

## Real review defects and repair

The former consumer called void emitters and returned zero without observing
their output; its claimed `ok:` line was wrong (the API emits `success:`).
The repaired consumer captures stdout and compares its exact length and bytes,
then restores/closes descriptors. Checks remain active under NDEBUG.

The former `host Check unavailable` declaration incorrectly skipped the whole
C upstream suite. Check is a target test-framework requirement, not a reason
to waive native testing. An isolated OHOS/armv8 `--build=never` resolution
downloaded check/0.15.2 with RREV 6d41c3078e77093b6b9dfe97b95e0f9c,
PID 21b17f8b2bc0e9511e276e3d57a23893067cefe5,
PREV 30d62eb1e36c4d31e934b687d33d3943 and empty exact-root info_invalid.
The unchanged six C test registrations run with that published static archive.
No framework source patch, no CK_FORK=no, no dropped test assertions.

The original first-run failure is preserved: Check could not create its
communication temporary file although TMPDIR was set. Existing E571 from
PR #9499 already explains TEMP-before-P_tmpdir. r002 adds task-private TEMP;
it does not modify libc, shared tools or the published framework.

## Target evidence

subunit-20261005-r005: full source-registration/Check XML identity equality,
6/6 original C cases; consumer 1/1; signed HarmonyOS PC HMDFS UTF-8 loader 1/1.
The single harness and its six cases are distinct denominators; the progress
case's four actions are not four cases. `test_skip` validates the public skip
emitter and is an executed successful test, not a framework skip.

WAL and receipt chain, unique launch=1, signed binary hashes, AFTER, zero own
live processes, release/postrelease and frozen validator all PASS. r001 remains
FAIL and is never spliced into r005. r002/r003/r004 are separately preserved prior
input validations. reports/r005-* retain current raw bytes and hashes.

Formal r002 exposed the package-level link failure: the real output was
libsubunit.so, but DT_SONAME/DT_NEEDED requested libsubunit.so.0 with no
matching file or runtime path. HarmonyOS now uses the actual basename as
SONAME and gives only the in-build upstream harness an origin-relative
RPATH. No installed package RPATH or shared cache mutation is introduced.
The corrected input closure passed native r004. Formal r003 then ran the
original six cases successfully but exposed a CMake OS-guard mismatch:
the native toolchain reports CMAKE_SYSTEM_NAME=HarmonyOS, while the consumer
project recognized only OHOS, so the required Harmony executable was absent.
The consumer now recognizes both CMake names; Conan settings.os remains OHOS.
Current input closure passed native r005; formal r004 is independent.

Two host-only synthetic XML/environment controls prove the wrapper accepts
the complete six IDs and rejects a zero-case RC0/100%-looking response. They
also verify inherited CK_RUN_CASE/CK_FORK are removed. These are diagnostic
controls, not native Check results and not additional product cases.

Current shared recipe, installed consumer, formal native Conan/local CI,
current-HEAD platform CI/Review and submission are separate gates. Cross
build-only output is never described as target execution. Upload and merge
remain outside this task.

Knowledge supplement: E2026100501-draft-2301_80739235, explicitly supplements
E571 / merged PR #9499 with environment-selector isolation and independently
registered-vs-runtime XML coverage. It does not re-claim the TEMP workaround.
