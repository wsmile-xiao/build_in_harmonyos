# Opus 1.4 adaptation notes

This Path A candidate uses the official Xiph 1.4 release archive, SHA-256
`c9b32b4253be5ae63d1ff16eea06b94b5f0f2951b7a02aceef58e3a3ce49c51f`.
It has no third-party dependency and is a required leaf for OpusFile.

The upstream Meson files configure SILK before the CELT variables consumed by
SILK on AArch64. The portability patches configure CELT first, produce the
expected unversioned OHOS shared-library shape, and invoke Meson Python helpers
through the Python interpreter. They do not alter codec sources or tests.

The complete Meson inventory has fourteen different executable paths: eight
CELT and one SILK component programs, plus five Opus API/codec integration
programs. The SILK test accidentally reuses the preceding CELT label, so the
recipe executes all fourteen paths directly rather than deduplicating labels.
The installed-package consumer adds one encode/decode flow. Shared and static
runs do not increase these counts.

Windows host Meson validation built and ran all fourteen upstream executable
paths with no failure, including both executables carrying the repeated
`test_unit_cwrs32` label. The installed shared package consumer completed one
silent-frame encode/decode and version check.

A fresh isolated Conan host `create` also completed the static package, all
fourteen direct upstream executable runs, package installation, CMakeDeps
consumer build, and the installed-package encode/decode process.

Fresh target W3 r10 completed both shared and static Conan creates after the
consumer cleanup and signed-file mode review fixes. Each variant
ran the same fourteen distinct upstream executable paths and one installed-package
consumer. Shared/static repetition does not increase the logical inventory. The
target result is 9/9 component, 5/5 upstream integration, and 1/1 consumer,
with all build variants and the runner exiting zero. The evidence archive is
`E:/HarmonyPC/validation/opus-1.4/device-r10-evidence.tar.gz`, SHA-256
`fabaa324089dbf56fcd772dfaf67e5c5c7d8bd047ea7545cfcfeba11af777c36`.
The runner verified all 17 candidate inputs before execution. The installed
shared library and consumer are AArch64 ELFs with exactly one `.codesign`
section each.

CI Build 10942 exposed that the OHOS profile supplies absolute `clang` and
`clang++` paths but leaves Meson's archive tools as bare `llvm-ar` and
`llvm-ranlib` names. The worker does not place the HNP toolchain directory on
`PATH`, so the recipe now resolves both tools next to the configured C compiler
and writes their absolute paths into the generated Meson native file.

The original r8 candidate used three functional patches. A later outer commit
check found whitespace-only context markers in those patch files, so the same
source changes were regenerated as nine patches with nonblank context. The r9
candidate keeps all seven non-patch inputs byte-identical to r8. Applying the
r8 and r9 series to the official archive produces the same 401-file source
tree. Standard `git apply`, GNU patch with zero fuzz, and Conan's patch-ng all
replay the r9 series successfully. The detailed proof is in
`reports/patch-equivalence-report.md`.

The r10 review-fix candidate still requires a new independent W4. CI,
publication, Issue, PR, and push remain pending.
