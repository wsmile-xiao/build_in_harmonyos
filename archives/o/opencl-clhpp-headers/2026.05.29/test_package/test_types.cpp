// test_types.cpp — Verify key OpenCL C++ types are defined
#include <CL/opencl.hpp>
#include <type_traits>

int main() {
    // Core wrapper types
    static_assert(std::is_class<cl::Platform>::value, "cl::Platform must be a class");
    static_assert(std::is_class<cl::Device>::value, "cl::Device must be a class");
    static_assert(std::is_class<cl::Context>::value, "cl::Context must be a class");
    static_assert(std::is_class<cl::CommandQueue>::value, "cl::CommandQueue must be a class");
    static_assert(std::is_class<cl::Buffer>::value, "cl::Buffer must be a class");
    static_assert(std::is_class<cl::Event>::value, "cl::Event must be a class");
    static_assert(std::is_class<cl::UserEvent>::value, "cl::UserEvent must be a class");
    static_assert(std::is_class<cl::Sampler>::value, "cl::Sampler must be a class");
    static_assert(std::is_class<cl::Program>::value, "cl::Program must be a class");
    static_assert(std::is_class<cl::Kernel>::value, "cl::Kernel must be a class");

    // Inheritance checks
    static_assert(std::is_base_of<cl::Event, cl::UserEvent>::value,
                  "cl::UserEvent must inherit from cl::Event");

    // Non-zero size (types are properly defined, not just forward-declared)
    static_assert(sizeof(cl::Platform) > 0, "cl::Platform must have non-zero size");
    static_assert(sizeof(cl::Device) > 0, "cl::Device must have non-zero size");
    static_assert(sizeof(cl::Context) > 0, "cl::Context must have non-zero size");
    static_assert(sizeof(cl::CommandQueue) > 0, "cl::CommandQueue must have non-zero size");

    return 0;
}
