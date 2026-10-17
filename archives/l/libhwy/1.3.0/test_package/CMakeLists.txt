cmake_minimum_required(VERSION 3.15)
project(test_libhwy CXX)

find_package(hwy REQUIRED)

add_executable(test_libhwy test_libhwy.cpp)
target_link_libraries(test_libhwy PRIVATE hwy::hwy)
target_compile_features(test_libhwy PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_libhwy COMMAND test_libhwy)
