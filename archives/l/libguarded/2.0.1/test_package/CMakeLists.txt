cmake_minimum_required(VERSION 3.15)
project(libguarded_consumer LANGUAGES CXX)

find_package(CsLibGuarded CONFIG REQUIRED)

add_executable(libguarded_consumer test_package.cpp)
target_compile_features(libguarded_consumer PRIVATE cxx_std_20)
target_link_libraries(libguarded_consumer PRIVATE CsLibGuarded::CsLibGuarded)

enable_testing()
add_test(NAME libguarded_consumer COMMAND libguarded_consumer)
