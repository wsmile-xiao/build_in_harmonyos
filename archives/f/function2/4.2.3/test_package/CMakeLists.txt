cmake_minimum_required(VERSION 3.11)
project(test_function2 LANGUAGES CXX)
enable_testing()
find_package(function2 REQUIRED CONFIG)

add_executable(test_function2 test.cpp)
target_link_libraries(test_function2 function2::function2)
add_test(NAME test_function2 COMMAND test_function2)

# HarmonyOS-specific consumer test (aarch64 OHOS toolchain)
add_executable(test_function2_hmos hmos_test.cpp)
target_link_libraries(test_function2_hmos function2::function2)
add_test(NAME test_function2_hmos COMMAND test_function2_hmos)
