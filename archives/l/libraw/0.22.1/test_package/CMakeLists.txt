cmake_minimum_required(VERSION 3.15)
# libraw is a C++ library (raw/raw_r built from .cpp); a pure C project would
# link with the C driver and miss the C++ runtime (std::, __cxa_*, operator
# new/delete) when linking the static lib. Declare C CXX so CMake uses the
# C++ linker for the final executable.
project(test_libraw C CXX)

# Find the libraw package via Conan-generated CMakeDeps.
# Conan's CMakeDeps creates the target libraw::libraw from cpp_info.libs.
find_package(libraw REQUIRED)

add_executable(test_libraw test.c)
target_link_libraries(test_libraw libraw::libraw)

enable_testing()
add_test(NAME test_libraw COMMAND test_libraw)
