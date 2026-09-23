cmake_minimum_required(VERSION 3.15)
project(test_kdtree C)

# Find the package via Conan-generated CMakeDeps
find_package(kdtree REQUIRED)

add_executable(test_kdtree test.c)
target_link_libraries(test_kdtree kdtree::kdtree)

# HarmonyOS-specific test case (native OHOS build+run, assert-based)
add_executable(test_kdtree_ohos test_ohos.c)
target_link_libraries(test_kdtree_ohos kdtree::kdtree)

enable_testing()
add_test(NAME test_kdtree COMMAND test_kdtree)
add_test(NAME test_kdtree_ohos COMMAND test_kdtree_ohos)
