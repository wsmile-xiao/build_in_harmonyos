# siege

siege is an HTTP/HTTPS load testing and benchmarking command-line tool.

## OpenHarmony Adaptation

Version `4.1.7` is adapted as a Conan application package for OHOS armv8.

Key points:
- Autotools in-source build is used because the upstream package does not fully support VPATH builds.
- SSL is disabled with `--without-ssl` because this recipe does not declare OpenSSL as a Conan dependency.
- OHOS pthread compatibility is handled for pthread ID storage and missing pthread cancellation APIs.

## Verification

See `4.1.7/reports/conan-verify-report.md` and `4.1.7/reports/test-report.md`.
