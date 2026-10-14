# libpagemaker 0.0.4 native adaptation notes

Shared-library scope; docs/tools disabled. Published dependencies librevenge/0.0.5, boost/1.90.0.3 and transitive zlib/1.3.1. Task-private .la-free librevenge archives and explicit header/zlib link closure; provider cache remains untouched.

r1: old config.sub parsed unknown linux-ohos as part of the machine, reporting aarch64-unknown-linux not recognized despite accepting aarch64 CPUs.
r2: add linux-ohos to BOTH initial kernel/OS tokenizer and terminal OS whitelist. config.guess early echo/exit matches the target compiler's aarch64-unknown-linux-ohos tuple. Use upstream --disable-werror while retaining warnings. Actual library is pagemaker-0.0, not pmd-0.0; include/pkg-config libpagemaker-0.0.

Official release has no registered test programs; make check executed successfully. No external suite claimed. Consumer uses LibreOffice/core shapes.pmd (blob 40e7df8b2f745986ea87653cb276487c36f92f95), 96256 bytes, SHA256 70e683a3c10c0d8a90bdb44fa534f531a72427ae9f77ad06c552cc8b2fbe68c8. Independent Git blob identity verified. Actual recognition and parsing produce 1 SVG page; HarmonyOS identity and TMPDIR lifecycle; 14 assertions.

Final run libpagemaker-conan-20261011T0700Z-r2: Conan RC0, release make check RC0, consumer PASS, all 12 receipts/release/postrelease PASS.
Candidate SHA256 3ce36eca9f43496b7016f8a9980dfd3733ea16b10df4daf1d9fcb528949c0579.
Log SHA256 9f8b2165d114fa6f32c6729f519c3927f0547def23a87afbbcb98493202e5eeb.

## Formal validation and submission preparation

Official two-patch candidate passed `libpagemaker-finish-20261011-r1`: conan-verify and embedded W3 PASS, make check RC0 with zero release-registered tests, independent consumer 14 assertions and one SVG page. Raw W3 SHA-256 3bba791cb0a75115f46bda63971df3c259d7689119bae886edd45d5763c07ddb; integrity dbabc432e493a7b0. All 12 receipts/release/postrelease PASS. Aggregate finish RC1 only legacy post-W3 step5b/step8 readiness/staging, not worker CI or whole-finish PASS.

Scope review against LibreOffice WpftDrawFilterTest.cxx / CppunitTest_writerperfect_draw.mk confirms a separate application/UNO filter suite, not a release-library registered target. It was NOT run or counted as passed. Release denominator 0/0 (not applicable); added independent consumer 1/1. Fixture provenance/project-license caveat is in test_package/FIXTURE-NOTICE.md. Source inventory, HD reassessment and E545-draft-PM11 completed; remote PRE/POST contracts still required. Subsequent attribution/scope wording is documentation only; recipe, patches, binary test inputs and fixture unchanged.
