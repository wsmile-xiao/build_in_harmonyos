#include <iostream>

int main() {
    // CMake 配置期已通过 rocm_setup_version 验证了包的核心 API
    // 此程序用于满足 Conan test_package 的运行时验证流程
    std::cout << "rocm-cmake consumer test: CMake configure-time API validation passed" << std::endl;
    return 0;
}
