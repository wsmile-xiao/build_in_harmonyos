cmake_minimum_required(VERSION 3.15)
project(test_clips C)

# Find the package via Conan-generated CMakeDeps
find_package(clips REQUIRED)

# API-level test: environment + rule engine round-trip
add_executable(test_clips test.c)
target_link_libraries(test_clips clips::clips)

# Consumer test: application loads external rules file at runtime
add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer clips::clips)

# HarmonyOS-specific platform tests: POSIX clock path + facts-file round trip
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos clips::clips)

enable_testing()
add_test(NAME test_clips COMMAND test_clips)
add_test(NAME test_consumer COMMAND test_consumer)
add_test(NAME test_ohos COMMAND test_ohos)
