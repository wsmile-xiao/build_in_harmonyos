# abootimg 0.6 adaptation notes

The upstream repository has no release tag, so this recipe pins commit
`7e127fee6a3981f6b0a50ce9910267cd501e09d4`, whose changelog and source report
version 0.6. The archive SHA-256 is recorded in `conandata.yml`.

The upstream Makefile only compiles one C source file. The recipe performs the
same compile directly so Conan can supply the OHOS Clang executable and build
type flags. The optional Linux `libblkid` guard is not enabled because OHOS
does not expose raw Linux block devices to this package; regular image-file
inspection, creation, extraction, and update paths remain available.

The exact upstream source contains no automated test directory or test target.
The consumer test creates an Android boot image from deterministic kernel and
ramdisk bytes, inspects it, and rejects a deliberately invalid image. Upstream
exits with the current `errno` after stdio failures; EOF can leave `errno` at
zero on OHOS, which incorrectly reports success. The portability patch keeps
the original errno when present and otherwise returns `EXIT_FAILURE`.
