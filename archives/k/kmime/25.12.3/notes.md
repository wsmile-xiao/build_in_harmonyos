# kmime 25.12.3 notes

## Scope

This package is required by `akonadi-mime/25.12.3` and later Akonadi
downstream PIM packages.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_TESTING=ON` runs upstream CTest autotests during Conan build.
- `BUILD_FUZZERS=OFF` keeps oss-fuzz helper targets out of the package build.
- `BUILD_QCH=OFF` skips API documentation generation.
- `ecm_install_po_files_as_qm(poqm)` is disabled because the Qt Linguist tools
  component is not part of the qtbase package used by this repository.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `fce3c603cac3fec9a3f0e101c49785c32ace07b8f60b52739b638d329f43826d`.
- The translation patch was checked against the unpacked 25.12.3 source.

OHOS `conan create` verification passed on 2026-08-27.

- Full package reference:
  `kmime/25.12.3#0fc08f3acd53bd78ce79c07b8b9065cc:5c5cd9f3b882ce5209e67c366e65bf761c3d2adc#da9738c272a632f309a6bb63b49f6407`.
- Upstream CTest: 16/16 passed.
- Conan `test_package`: 1/1 passed.
