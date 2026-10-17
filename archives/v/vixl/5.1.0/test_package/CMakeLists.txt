cmake_minimum_required(VERSION 3.15)
project(test_vixl CXX)

find_package(vixl REQUIRED)

add_executable(test_vixl test.cpp)
target_link_libraries(test_vixl VIXL::vixl)
target_compile_features(test_vixl PRIVATE cxx_std_14)

enable_testing()
add_test(NAME test_vixl COMMAND test_vixl)
