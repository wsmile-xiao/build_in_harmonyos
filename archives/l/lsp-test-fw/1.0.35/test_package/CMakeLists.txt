cmake_minimum_required(VERSION 3.15)
project(test_lsp-test-fw CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(lsp-test-fw REQUIRED)

add_executable(test_lsp-test-fw test.cpp)
target_link_libraries(test_lsp-test-fw PRIVATE lsp-test-fw::lsp-test-fw)
