#define gsl_CONFIG_DEFAULTS_VERSION 1
#include <gsl-lite/gsl-lite.hpp>
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v{1, 2, 3, 4, 5};
    gsl::span<int> s(v);
    if (s.size() != 5) {
        std::cerr << "FAIL: span size = " << s.size() << ", expected 5" << std::endl;
        return 1;
    }
    std::cout << "gsl-lite test OK: span size=" << s.size()
              << " first=" << s[0] << " last=" << s[4] << std::endl;
    return 0;
}
