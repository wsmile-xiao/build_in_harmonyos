cmake_minimum_required(VERSION 3.15)
project(test_libigloo C)

# Find the package via Conan-generated CMakeDeps
find_package(libigloo REQUIRED)

add_executable(test_libigloo test.c)
target_link_libraries(test_libigloo libigloo::libigloo)

enable_testing()
add_test(NAME test_libigloo COMMAND test_libigloo)

# OHOS-specific artifact check: the consumer binary itself must be a
# 64-bit little-endian ELF targeting AArch64 (EM_AARCH64). The checker
# exits non-zero on any mismatch — no stub, no skip.
add_executable(check_ohos_elf ohos_elf_check.c)
add_test(NAME check_ohos_elf COMMAND check_ohos_elf $<TARGET_FILE:test_libigloo>)
