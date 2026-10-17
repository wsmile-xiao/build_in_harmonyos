cmake_minimum_required(VERSION 3.15)
project(test_easyloggingpp CXX)

find_package(easyloggingpp REQUIRED)

add_executable(test_easyloggingpp test.cpp)
target_link_libraries(test_easyloggingpp PRIVATE easyloggingpp::easyloggingpp)
set_target_properties(test_easyloggingpp PROPERTIES CXX_STANDARD 14 CXX_STANDARD_REQUIRED ON)
