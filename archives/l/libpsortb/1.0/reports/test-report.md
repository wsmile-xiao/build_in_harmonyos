# libpsortb 1.0 target-device test report

Date: 2026-09-25. Task: #8343. Team: 诶，云朵. Candidate path: B (knowledge extension), subject to event review.

## Source and build scope

- Source: Debian `libpsortb_1.0+dfsg.orig.tar.xz`, SHA-256 `5021b7ac656b33b8f0aa8c2e0403056a5459e1b92c17008b3ff442e262b3e2e5`. The upstream download returned HTTP 403 from this host.
- The DFSG repack retains `svmloc` and `modhmm0.92b`; this package builds only their `libsvmloc` and `libmodhmm` shared libraries. It does **not** claim to package the original bundled HMMER, SQUID, or full PSORTb application.
- The 10-file portability/API patch applied to a fresh source extraction using Conan's `patch_ng` with `fuzz=False`. Dependencies: `libsvm/3.37.1.1` plus published Autoconf, Automake, and Libtool tools.

## Actual HarmonyOS PC result

- Device: the same shared HarmonyOS PC as earlier work; its campus-network IP is dynamic and intentionally omitted from this public report. OS target aarch64 / OHOS 6.0, Clang 15, Conan 2.29.1. The private run receipt records the host identity and process ownership for verification.
- Final run ID: `libpsortb-w3-20260925T065340Z`. Exact recipe/source bundle SHA-256 `2ec2384312fc756de9a45f962b85bae10ce9925e4654e982b68796df0fb98bbb`; target transfer, eight input hashes, chained receipts, release, postrelease, and read-only validator all passed. The run was launched once.
- Command inside the frozen runner: `conan create <run>/input/recipe --profile:host <run>/input/ohos-profile --profile:build <run>/input/ohos-profile --build='libpsortb/*' -r=ohpcd`. `LIBPSORTB_SOURCE_ARCHIVE` points to the exact transferred source archive; the recipe still verifies its conandata SHA-256. Conan used an isolated cache and temporary directory.
- `conan create` returned 0, built and installed both shared libraries, and ran `test_package` on the target. The installed-package consumer compiled against the Conan-generated CMake target, created/inspected/destroyed an SVM and checked modhmm's `get_mtx_index`, `itoa`, and `ftoa`; result `LIBPSORTB_CONSUMER_PASS` (1/1 executable, six checks).
- `make check -j1` ran and returned 0. The retained upstream Makefile.am files define no `TESTS`, `check_PROGRAMS`, or check-local target, so this is **0/0 upstream test cases**, not evidence of a passing functional suite. No upstream tests were modified.
- The frozen final log SHA-256 is `fdc056d434ad713a559966a104278528cfc7b33e19e3ca51108441f09bd04dbe`; final receipt-chain head SHA-256 is `e82e1e7b33d34323a0868f04e76e5e0ca7608939b7d2b991899459d26b74c1c5`. `W3_VALIDATOR_PASS` confirmed the complete chain and independent readback confirmed the log/test markers.

## Diagnosed failures and remaining limits

- Earlier target runs exposed a broken published Automake wrapper/Perl module path, unrecognized build triplet, and old C pointer/signature mismatches. Each diagnostic run had a unique root and was released without relaunching. The final recipe invokes the published Automake real scripts through the native Perl interpreter with package-local macro/module paths; the source patch fixes only necessary C/C++ compatibility issues.
- The preceding run `libpsortb-w3-20260925T062500Z` built and installed the package but its consumer could not find public `<svm.h>`. The final recipe declares `libsvm` as a transitive-header requirement and a `cpp_info.requires` edge; the final consumer then compiled, linked, and ran.
- Old `modhmm` source still emits compiler warnings. The available functional coverage is one consumer executable and no upstream cases; this is not a claim of complete PSORTb application functionality.
- No platform CI result, PR review, merge, package-registry publication, or score approval is claimed.
