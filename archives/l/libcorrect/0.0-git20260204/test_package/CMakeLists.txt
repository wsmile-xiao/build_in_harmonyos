cmake_minimum_required(VERSION 3.15)
project(test_correct C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

enable_testing()

# Find the package via Conan-generated CMakeDeps (recipe exports
# cmake_file_name "correct" / cmake_target_name "correct::correct")
find_package(correct REQUIRED)

# Consumer test 1: library API roundtrips
add_executable(test_correct test_correct.c)
target_link_libraries(test_correct PRIVATE correct::correct)
add_test(NAME test_correct COMMAND test_correct)

# Consumer test 2 (OHOS-specific, rule12): OHOS musl runtime + aarch64
# platform asserts + independent parameter roundtrips
add_executable(test_correct_ohos test_correct_ohos.c)
target_link_libraries(test_correct_ohos PRIVATE correct::correct)
add_test(NAME test_correct_ohos COMMAND test_correct_ohos)
