cmake_minimum_required(VERSION 3.15)
project(test_opendht LANGUAGES CXX)

find_package(opendht REQUIRED)

add_executable(test_opendht test.cpp)
target_compile_features(test_opendht PRIVATE cxx_std_17)
target_link_libraries(test_opendht PRIVATE opendht)

enable_testing()
add_test(NAME test_opendht COMMAND test_opendht)
