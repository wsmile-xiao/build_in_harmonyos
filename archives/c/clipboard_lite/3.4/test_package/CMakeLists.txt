cmake_minimum_required(VERSION 3.15)
project(test_clipboard_lite CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(clipboard_lite REQUIRED)

add_executable(test_clipboard_lite consumer.cpp)
target_link_libraries(test_clipboard_lite clipboard_lite::clipboard_lite)