cmake_minimum_required(VERSION 3.11)
project(test_libpopcnt LANGUAGES C CXX)
enable_testing()
find_package(libpopcnt REQUIRED CONFIG)

add_executable(test_libpopcnt test.c)
target_link_libraries(test_libpopcnt PRIVATE libpopcnt::libpopcnt)
add_test(NAME test_libpopcnt COMMAND test_libpopcnt)

# HarmonyOS-specific consumer test (aarch64 OHOS toolchain / verification path)
add_executable(test_libpopcnt_hmos test_hmos.c)
target_link_libraries(test_libpopcnt_hmos PRIVATE libpopcnt::libpopcnt)
add_test(NAME test_libpopcnt_hmos COMMAND test_libpopcnt_hmos)
