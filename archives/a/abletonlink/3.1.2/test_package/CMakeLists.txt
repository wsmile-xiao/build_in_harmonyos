cmake_minimum_required(VERSION 3.15)
project(test_abletonlink LANGUAGES CXX)

find_package(abletonlink CONFIG REQUIRED)

add_executable(test_abletonlink test.cpp)
target_compile_features(test_abletonlink PRIVATE cxx_std_17)
target_link_libraries(test_abletonlink PRIVATE abletonlink::abletonlink)

enable_testing()
add_test(NAME test_abletonlink COMMAND test_abletonlink)
