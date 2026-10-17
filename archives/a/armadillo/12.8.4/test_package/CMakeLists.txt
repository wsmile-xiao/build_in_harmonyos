cmake_minimum_required(VERSION 3.15)
project(test_armadillo LANGUAGES CXX)

find_package(Armadillo CONFIG REQUIRED)

add_executable(test_armadillo test.cpp)
target_compile_features(test_armadillo PRIVATE cxx_std_14)
target_link_libraries(test_armadillo PRIVATE Armadillo::Armadillo)

enable_testing()
add_test(NAME test_armadillo COMMAND test_armadillo)
