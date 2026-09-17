cmake_minimum_required(VERSION 3.15)
project(darts_test CXX)

find_package(darts CONFIG REQUIRED)

add_executable(darts_test test.cpp)
target_link_libraries(darts_test PRIVATE darts::darts)
target_compile_features(darts_test PRIVATE cxx_std_17)

enable_testing()
add_test(NAME darts_test COMMAND darts_test)
