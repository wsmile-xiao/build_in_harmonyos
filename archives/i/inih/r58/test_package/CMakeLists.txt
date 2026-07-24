cmake_minimum_required(VERSION 3.15)

# OHOS: CMake 4.1.2 cannot fully verify C compiler on unknown platforms
# (HarmonyOS). Bypass the compiler-test-executable step; linking works
# fine at actual build time via the Conan toolchain compiler setting.
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

project(test_inih C)

# Find the package via Conan-generated CMakeDeps
find_package(inih REQUIRED)

add_executable(test_inih test_inih.c)
target_link_libraries(test_inih inih::inih)

enable_testing()
add_test(NAME test_inih COMMAND test_inih)
