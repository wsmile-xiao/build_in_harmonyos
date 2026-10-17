#include <CL/opencl.hpp>

int main() {
    // Compile-time verification: the header is includable and the
    // CL_HPP_TARGET_OPENCL_VERSION macro is defined correctly
    static_assert(CL_HPP_TARGET_OPENCL_VERSION >= 200,
                  "OpenCL C++ header version check failed");
    return 0;
}
