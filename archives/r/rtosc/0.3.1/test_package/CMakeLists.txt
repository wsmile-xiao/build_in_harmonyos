cmake_minimum_required(VERSION 3.15)
project(test_rtosc CXX C)

find_package(rtosc REQUIRED)

add_executable(test_rtosc test_rtosc.cpp)
target_link_libraries(test_rtosc rtosc::rtosc)
target_compile_features(test_rtosc PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_rtosc COMMAND test_rtosc)
