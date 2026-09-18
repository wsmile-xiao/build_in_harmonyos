cmake_minimum_required(VERSION 3.15)
project(test_libpfm4 C)

find_package(libpfm4 REQUIRED)

# Note: once CTest is enabled CMake reserves the target name "test", hence the
# first program is built as test_api (source file stays test.c).

# test_api               - public API: PMU/event discovery, lookup, encoding
add_executable(test_api test.c)
target_link_libraries(test_api PRIVATE libpfm4::libpfm4)

# test_upstream_validate - the upstream event table suite (tests/validate.c)
add_executable(test_upstream_validate test_upstream_validate.c)
target_link_libraries(test_upstream_validate PRIVATE libpfm4::libpfm4)

# test_ohos              - HarmonyOS specifics: ABI size constants, perf_events PMU
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PRIVATE libpfm4::libpfm4)

enable_testing()
add_test(NAME test_api COMMAND test_api)
add_test(NAME test_upstream_validate COMMAND test_upstream_validate)
add_test(NAME test_ohos COMMAND test_ohos)
