cmake_minimum_required(VERSION 3.15)
project(test_link_grammar LANGUAGES CXX)

find_package(link-grammar CONFIG REQUIRED)

add_executable(test_link_grammar test.cpp)
target_compile_features(test_link_grammar PRIVATE cxx_std_17)
target_link_libraries(test_link_grammar PRIVATE link-grammar::link-grammar)
