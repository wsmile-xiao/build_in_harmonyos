#include <cstring>
#include <iostream>
#include <string>

extern "C" {
#include <libscap/scap.h>
}
#include <libsinsp/utils.h>

int main() {
    const char* syscall_name = scap_get_ppm_sc_name(PPM_SC_OPEN);
    if (syscall_name == nullptr || std::strcmp(syscall_name, "open") != 0) {
        std::cerr << "scap_get_ppm_sc_name returned an unexpected value\n";
        return 1;
    }

    const std::string hostname = sinsp_gethostname();
    if (hostname.empty()) {
        std::cerr << "sinsp_gethostname returned an empty hostname\n";
        return 2;
    }

    std::cout << "falcosecurity-libs API test passed: " << syscall_name
              << ", hostname=" << hostname << "\n";
    return 0;
}
