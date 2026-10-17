cmake_minimum_required(VERSION 3.15)
project(test_libhwy_contrib CXX)

find_package(hwy_contrib REQUIRED)

add_executable(test_libhwy_contrib test_libhwy_contrib.cpp)
target_link_libraries(test_libhwy_contrib PRIVATE hwy::hwy_contrib)
target_compile_features(test_libhwy_contrib PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_libhwy_contrib COMMAND test_libhwy_contrib)
