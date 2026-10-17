cmake_minimum_required(VERSION 3.15)
project(test_zstr CXX)

find_package(zstr REQUIRED CONFIG)
find_package(ZLIB REQUIRED CONFIG)

add_executable(test_zstr test_zstr.cpp)
target_link_libraries(test_zstr PRIVATE zstr::zstr ZLIB::ZLIB)
target_compile_features(test_zstr PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_zstr COMMAND test_zstr)
