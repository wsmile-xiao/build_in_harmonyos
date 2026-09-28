cmake_minimum_required(VERSION 3.15)
project(test_tiny-aes-c C)

# Find the package via Conan-generated CMakeDeps
find_package(tiny-aes-c REQUIRED)

add_executable(test_tiny-aes-c test.c)
target_link_libraries(test_tiny-aes-c tiny-aes-c::tiny-aes-c)

# HarmonyOS PC specific test (rule12): AES-CBC encrypt -> write -> read back -> decrypt
# via the TMPDIR/HOME/tmp temp file convention, verifying E002 /tmp read-only.
add_executable(test_harmony test_harmony.c)
target_link_libraries(test_harmony tiny-aes-c::tiny-aes-c)

enable_testing()
add_test(NAME test_tiny-aes-c COMMAND test_tiny-aes-c)
add_test(NAME test_harmony COMMAND test_harmony)
