# BLIS 2.1 on OpenHarmony

The recipe targets BLIS' upstream `arm64` configuration for OpenHarmony aarch64.
It builds a static, single-threaded library and enables the CBLAS compatibility
header. The upstream numerical testsuite is run with `make check` during build.
