cmake_minimum_required(VERSION 3.15)
project(test_ewahboolarray LANGUAGES CXX)

find_package(ewahboolarray CONFIG REQUIRED)

add_executable(test_ewahboolarray test.cpp)
target_compile_features(test_ewahboolarray PRIVATE cxx_std_11)
target_link_libraries(test_ewahboolarray PRIVATE ewah::ewah)

enable_testing()
add_test(NAME test_ewahboolarray COMMAND test_ewahboolarray)
