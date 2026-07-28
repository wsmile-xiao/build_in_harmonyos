cmake_minimum_required(VERSION 3.15)
project(test_watcher CXX)

find_package(watcher REQUIRED)

add_executable(test_watcher test.cpp)
target_link_libraries(test_watcher watcher::watcher)
target_compile_features(test_watcher PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_watcher COMMAND test_watcher)
