cmake_minimum_required(VERSION 3.15)
project(test_libosmium CXX)

find_package(libosmium REQUIRED)

add_executable(test_libosmium test.cpp)
target_link_libraries(test_libosmium PRIVATE libosmium::libosmium)
target_compile_features(test_libosmium PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_libosmium COMMAND test_libosmium)
