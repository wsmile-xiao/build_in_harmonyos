cmake_minimum_required(VERSION 3.15)
project(boost_json_consumer CXX)

find_package(boost1.84-json CONFIG REQUIRED)
add_executable(boost_json_test test_json.cpp)
target_link_libraries(boost_json_test PRIVATE boost1.84-json::boost1.84-json)
target_compile_features(boost_json_test PRIVATE cxx_std_17)

enable_testing()
add_test(NAME boost_json_test COMMAND boost_json_test)
