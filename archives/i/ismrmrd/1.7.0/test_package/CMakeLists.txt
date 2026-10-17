cmake_minimum_required(VERSION 3.15)
project(test_ismrmrd C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ismrmrd REQUIRED)

add_executable(test_ismrmrd test.c)
target_link_libraries(test_ismrmrd ismrmrd::ismrmrd)

add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos ismrmrd::ismrmrd)

enable_testing()
add_test(NAME test_ismrmrd COMMAND test_ismrmrd)
add_test(NAME test_ohos COMMAND test_ohos)
