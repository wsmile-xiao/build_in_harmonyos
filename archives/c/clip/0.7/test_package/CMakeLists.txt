cmake_minimum_required(VERSION 3.15)
project(test_clip CXX)

set(CMAKE_CXX_STANDARD 17)

find_package(clip REQUIRED)

add_executable(test_clip test.cpp)
target_link_libraries(test_clip clip::clip)

enable_testing()
add_test(NAME test_clip COMMAND test_clip)
