# libwpg 0.3.4 native adaptation notes

Shared-library scope, command-line tools and documentation disabled. Dependencies librevenge/0.0.5, libwpd/0.10.3, boost/1.90.0.3 and transitive zlib/1.3.1 downloaded as published binaries.
Private .la-free archive directory includes the three librevenge archives and libwpd-0.10.a. Preserve header closure and explicit zlib link closure without modifying provider caches.

r1 failed because config.guess recognized the compiler-proven aarch64-unknown-linux-ohos tuple, but modern config.sub rejected OS ohos.
r2 added both the OS acceptance and linux-ohos kernel/OS combination to source config.sub. Full configure/build/install/package/consumer now PASS. Correct public include and pkg-config names are libwpg-0.3; library wpg-0.3.

Official release has no registered test programs; make check still executed successfully. This is not a claim that all externally maintained LibwpgTest tests were run; that scope must be resolved before PR.
Consumer: official LibreOffice/core WPG1.wpg (blob 273089649c5a2bda843e4331ba5339cfee7fa447), 79 bytes, SHA256 10dbb1c7b6c81e87c69a971bc39ec5a7773e128812d2fc71d7b620d51d885dc3. Independent Git blob identity verified. Actual recognition and parse produce 1 SVG page; HarmonyOS identity and TMPDIR lifecycle; 14 assertions.

Final run libwpg-conan-20261011T0700Z-r2: Conan RC0, release make check RC0, consumer PASS, all 12 receipts/release/postrelease PASS.
Candidate SHA256 03044fd81572f8e4152b63a3d46e0f3adaa900006b592070ef600936e0fa85ad.
Log SHA256 610c5b5a979fcf895728af5de81168466b3f09ecb15ecc9d4a1a499acdb785c9.

## Formal validation and submission preparation

Official two-patch candidate passed `libwpg-finish-20261011-r1`: conan-verify and embedded W3 PASS, make check RC0 with zero release-registered tests, independent consumer 14 assertions and one SVG page. Raw W3 SHA-256 27cd0fe0d75da36f243203b87f60561d47fdce8541de267a8ec8bdc8de6d7686; integrity e45009925b46235a. All 12 receipts/release/postrelease PASS. Aggregate finish RC1 only legacy post-W3 step5b/step8 readiness/staging, not worker CI or whole-finish PASS.

Scope review completed against LibreOffice writerperfect/qa/unit/WpftDrawFilterTest.cxx and CppunitTest_writerperfect_draw.mk: this is a separate application filter integration suite with UNO/VCL/services, not registered by libwpg's release Makefile.am. It was NOT run; the release denominator remains 0/0 (not applicable), and the added consumer remains 1/1. External fixture provenance and project-license caveat are documented in test_package/FIXTURE-NOTICE.md. Inventory, HD reassessment and E545-draft-WG11 completed; remote PRE/POST contracts still required. Only documentation/attribution was updated after the formal run, not recipe, patch, executable or fixture bytes.
