// pybind11 3.1.0 test_package — 消费者视角编译/运行探测
// R34：实质依赖被测包 API —— 包含 pybind11 主头文件，使用其公开宏
// PYBIND11_VERSION_MAJOR/MINOR/PATCH/HEX 与 PYBIND11_CPP17 校验版本与
// 语言模式，并在运行期输出校验结果。
#include <pybind11/pybind11.h>

#include <cstdio>

namespace py = pybind11;

int main() {
    // 版本宏来自 pybind11 头文件（被测包 public API）
    static_assert(PYBIND11_VERSION_MAJOR == 3, "major version mismatch");
    static_assert(PYBIND11_VERSION_MINOR == 1, "minor version mismatch");
    static_assert(PYBIND11_VERSION_PATCH == 0, "patch version mismatch");
    static_assert(PYBIND11_VERSION_HEX == 0x030100F0, "version hex mismatch");

    // PYBIND11_CPP17 由 pybind11 头文件根据语言标准定义（public 宏）
#ifdef PYBIND11_CPP17
    const bool cxx17 = true;
#else
    const bool cxx17 = false;
#endif
    std::printf("pybind11 %d.%d.%d (hex 0x%08X) CXX17=%s\n",
                PYBIND11_VERSION_MAJOR, PYBIND11_VERSION_MINOR,
                PYBIND11_VERSION_PATCH, PYBIND11_VERSION_HEX,
                cxx17 ? "yes" : "no");
    return 0;
}