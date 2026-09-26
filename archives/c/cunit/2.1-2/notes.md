# CUnit 2.1-2 OHOS adaptation notes

- Source: the official `CUnit-2.1-2-src.tar.bz2` release from SourceForge.
- CI source: Conan downloads the official release from SourceForge's Netix mirror and verifies the unchanged upstream SHA-256 `1f705f30b36fe1dadb5494989d1d663241603f456b468c81f606a1bdbc168bea`. The archive is not stored in the PR, keeping the diff small enough for worker checkout.
- Build: compile the upstream Framework, Basic, Automated, and Console sources with the selected OHOS C compiler and archive them as `libcunit.a`.
- Headers: generate `CUnit.h` from the upstream template with version `2.1-2`.
- Upstream tests: the release has no registered `TESTS` or `check_PROGRAMS`; the optional internal test mode references `test_cunit.h` and five `Framework/*_test.c` files that are absent from the published tarball.
- Consumer verification: three CUnit API test cases compile, link, and run through `test_package`.
