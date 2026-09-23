cmake_minimum_required(VERSION 3.15)
project(test_zmqpp CXX)

find_package(zmqpp CONFIG REQUIRED)

add_executable(test_zmqpp test_zmqpp.cpp)
target_link_libraries(test_zmqpp PRIVATE zmqpp::zmqpp)
set_property(TARGET test_zmqpp PROPERTY CXX_STANDARD 11)
set_property(TARGET test_zmqpp PROPERTY CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_zmqpp COMMAND test_zmqpp)
