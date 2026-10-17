# kmbox 25.12.3 notes

## Scope

This package provides `KPim6::Mbox`, the KDE PIM mbox storage library used by
later Akonadi mail components.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE PIM build on OHOS.
- `KF_SKIP_PO_PROCESSING=ON` skips translation catalog generation.
- `BUILD_QCH=OFF` skips optional API documentation generation.
- `BUILD_TESTING=ON` keeps upstream CTest enabled during package creation.
- `0001-Skip-read-only-permission-autotest-on-OHOS.patch` skips only
  `MboxTest::testReadOnlyMbox()`. That subtest depends on chmod making a file
  reopen as read-only through `QFile`; the OHOS target runtime keeps that file
  writable from the test process, so the upstream assertion cannot be satisfied
  as a library behavior check.
- Runtime verification stages dependency libraries beside test executables for
  OHOS loader behavior around relative shared-library lookups.

## Verification

- Source archive SHA256 was verified against
  `088e88b85686374da855215351e0e5248464921c8b546531d91b8dcef952ff93`.
- OHOS aarch64 `conan create` passed.
- Full package reference:
  `kmbox/25.12.3#f2c7e7a5752555fe3c3afad32b6ac010:e3484c7f17adc480d011a8bb536147a4d28023c1#494482fb340b3e125ee0c9849e12580f`.
- Upstream CTest registered `mbox-mboxtest` and `mbox-mboxbenchmark`; 2/2
  CTest entries passed.
- The Conan `test_package` found `KPim6Mbox`/`KPim6::Mbox`, linked a CMake
  consumer, ran CTest 1/1, and directly verified write/save/reload/read of a
  MIME message through `KPim6::Mbox`.

## Upstream Tests Not Run

- `MboxTest::testReadOnlyMbox()` is skipped on OHOS by a test-only patch. It
  is hard-blocked by target file-permission semantics: after the test changes
  the mbox file to read-owner permissions, `QFile` can still reopen it with
  write access, so upstream's expected transition to `MBox::isReadOnly()` does
  not occur. The rest of `mbox-mboxtest`, including append, save/load, purge,
  header reading, lock timeout, and no-lock behavior, still runs.
- Appstream, outbound-license, and QCH documentation checks were not registered
  as library tests because their host-side optional tools were unavailable or
  documentation generation was disabled.
