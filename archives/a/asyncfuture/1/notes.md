# asyncfuture 1

The task version `1` packages upstream `v0.4.1` of benlau/asyncfuture.
The upstream qmake unit-test target is skipped on OHOS because the vendor/QPM dependency `com.github.benlau.testable@1.0.2.19` is unavailable. The installed header-only package is validated by the real `test_package` consumer test.
Qt 5.15.2.2 is supplied by the already-merged qt5-qtbase dependency recipe.
## Verification note

The upstream qmake unit test depends on a vendor package that is not present in the OHOS Conan graph, so the recipe relies on `test_package` for executable validation.
