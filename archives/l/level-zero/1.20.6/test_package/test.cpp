#include <level_zero/ze_api.h>
#include <level_zero/loader/ze_loader.h>
#include <iostream>
#include <cstdlib>

int main() {
    ze_result_t result = zeInit(0);
    std::cout << "zeInit returned: " << result << std::endl;
    // zeInit may fail with ZE_RESULT_ERROR_UNINITIALIZED when no GPU driver is
    // present; treat that as acceptable, any other error as a real failure.
    if (result != ZE_RESULT_SUCCESS && result != ZE_RESULT_ERROR_UNINITIALIZED) {
        std::cerr << "zeInit failed with unexpected error: " << result << std::endl;
        return 1;
    }

    size_t numComponents = 0;
    result = zelLoaderGetVersions(&numComponents, nullptr);
    std::cout << "zelLoaderGetVersions returned: " << result
              << ", numComponents: " << numComponents << std::endl;
    // The loader itself must always be loadable and report its version info,
    // independent of any GPU driver; a non-success here means a broken package.
    if (result != ZE_RESULT_SUCCESS) {
        std::cerr << "zelLoaderGetVersions failed: loader not usable" << std::endl;
        return 1;
    }

    std::cout << "Level-Zero API smoke test passed." << std::endl;
    return 0;
}
