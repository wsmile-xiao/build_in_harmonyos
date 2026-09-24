cmake_minimum_required(VERSION 3.15)
project(intel_hdcp_test LANGUAGES CXX)

enable_testing()

find_package(IntelHdcp REQUIRED)

add_executable(example example.cpp)
target_link_libraries(example PRIVATE IntelHdcp::IntelHdcp)

add_test(NAME example COMMAND example)