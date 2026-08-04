/// test_package for SoapySDR 0.8.1
/// Calls real C API functions to verify the library is usable.
#include <cstdio>
#include <cstring>
#include <SoapySDR/Version.h>

int main(void)
{
    // Test 1: get API version string
    const char *api = SoapySDR_getAPIVersion();
    if (api == nullptr) {
        std::fprintf(stderr, "FAIL: SoapySDR_getAPIVersion() returned null\n");
        return 1;
    }
    std::printf("SoapySDR API version: %s\n", api);

    // Test 2: get ABI version string
    const char *abi = SoapySDR_getABIVersion();
    if (abi == nullptr) {
        std::fprintf(stderr, "FAIL: SoapySDR_getABIVersion() returned null\n");
        return 1;
    }
    std::printf("SoapySDR ABI version: %s\n", abi);

    // Verify ABI matches compile-time constant
    if (std::strcmp(abi, SOAPY_SDR_ABI_VERSION) != 0) {
        std::fprintf(stderr, "FAIL: ABI mismatch (runtime=%s, compile-time=%s)\n",
                     abi, SOAPY_SDR_ABI_VERSION);
        return 1;
    }

    // Test 3: get library version string
    const char *libver = SoapySDR_getLibVersion();
    if (libver == nullptr) {
        std::fprintf(stderr, "FAIL: SoapySDR_getLibVersion() returned null\n");
        return 1;
    }
    std::printf("SoapySDR lib version: %s\n", libver);

    std::printf("All SoapySDR API tests passed.\n");
    return 0;
}