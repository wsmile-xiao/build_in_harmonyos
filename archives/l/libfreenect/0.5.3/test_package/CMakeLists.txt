cmake_minimum_required(VERSION 3.15)
project(test_libfreenect C)

# Find the package via the Conan-generated CMakeDeps config.
find_package(libfreenect REQUIRED)

add_executable(test_freenect test_freenect.c)
target_link_libraries(test_freenect libfreenect::libfreenect)

add_executable(test_sync test_sync.c)
target_link_libraries(test_sync libfreenect::libfreenect)

# HarmonyOS-specific: dlopen the signed shared libs to validate ELF signing.
# dlopen lives in libc on OHOS/musl; no separate -ldl to link.
add_executable(test_harmony test_harmony.c)

enable_testing()
add_test(NAME test_freenect COMMAND test_freenect)
add_test(NAME test_sync COMMAND test_sync)
add_test(NAME test_harmony COMMAND test_harmony)
