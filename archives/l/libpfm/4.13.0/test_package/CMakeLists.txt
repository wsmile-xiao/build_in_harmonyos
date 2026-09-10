cmake_minimum_required(VERSION 3.15)
project(test_libpfm C)

# Find the package via Conan-generated CMakeDeps
find_package(libpfm REQUIRED)

add_executable(test_libpfm test.c)
target_link_libraries(test_libpfm libpfm::libpfm)

# HarmonyOS PC (aarch64) specific test: ARM64 perf_event encoding via the
# packaged libpfm (real platform adaptation verification, R34).
add_executable(test_libpfm_harmonyos harmonyos_test.c)
target_link_libraries(test_libpfm_harmonyos libpfm::libpfm)

enable_testing()
add_test(NAME test_libpfm COMMAND test_libpfm)
add_test(NAME test_libpfm_harmonyos COMMAND test_libpfm_harmonyos)
