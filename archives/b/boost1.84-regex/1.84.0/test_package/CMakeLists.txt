cmake_minimum_required(VERSION 3.15)
project(boost_regex_consumer CXX)

find_package(boost1.84-regex CONFIG REQUIRED)
add_executable(boost_regex_test test_regex.cpp)
target_link_libraries(boost_regex_test PRIVATE boost1.84-regex::boost1.84-regex)
target_compile_features(boost_regex_test PRIVATE cxx_std_17)

enable_testing()
add_test(NAME boost_regex_test COMMAND boost_regex_test)
