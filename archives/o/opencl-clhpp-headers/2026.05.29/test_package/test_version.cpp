// test_version.cpp — Verify OpenCL C++ header version macros
#include <CL/opencl.hpp>

int main() {
    // CL_HPP_TARGET_OPENCL_VERSION must be defined and >= 200
    static_assert(CL_HPP_TARGET_OPENCL_VERSION >= 200,
                  "CL_HPP_TARGET_OPENCL_VERSION must be >= 200");

    // CL_HPP_MINIMUM_OPENCL_VERSION must be defined and >= 120
    static_assert(CL_HPP_MINIMUM_OPENCL_VERSION >= 120,
                  "CL_HPP_MINIMUM_OPENCL_VERSION must be >= 120");

    // Target version must be >= minimum version
    static_assert(CL_HPP_TARGET_OPENCL_VERSION >= CL_HPP_MINIMUM_OPENCL_VERSION,
                  "Target version must be >= minimum version");

    return 0;
}
