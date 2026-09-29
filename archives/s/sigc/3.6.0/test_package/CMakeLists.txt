cmake_minimum_required(VERSION 3.15)
project(test_sigc_consumer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libsigc REQUIRED)

add_executable(test_sigc_consumer sigc_consumer_case.cpp)
target_link_libraries(test_sigc_consumer PRIVATE libsigc::libsigc)
