# prison 6.18.0 notes

## Scope

This package provides `KF6::Prison`, used by `akonadi-contacts` widgets.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE Frameworks build on OHOS.
- `WITH_QUICK=OFF` and `WITH_MULTIMEDIA=OFF` keep scanner/Qt Quick support out
  of the baseline package.
- `CMAKE_DISABLE_FIND_PACKAGE_Dmtx=ON` and
  `CMAKE_DISABLE_FIND_PACKAGE_ZXing=ON` avoid optional barcode scanner/format
  paths that are not required by `akonadi-contacts`.
- `QRencode_LIBRARIES` and `QRencode_INCLUDE_DIRS` are set from the
  `qrencode/4.1.1` package because upstream uses a manual `FindQRencode.cmake`.
- `BUILD_TESTING=ON` keeps upstream CTest coverage enabled.

## Verification

OHOS `conan create` passed:

- Upstream CTest: 5/5 passed.
- test_package CTest: 1/1 passed.
- Direct test executable: `PASS: Prison QR image 99x99`.
- Full package reference:
  `prison/6.18.0#39493ce15b1566f64a766eec250cb27c:0301f160c3baf1aaa17e519ad57459451098ba3f#fb35632444b62d295d616a908566deee`.
