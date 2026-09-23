cmake_minimum_required(VERSION 3.15)
project(test_kcompletion CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF6Completion REQUIRED)

add_executable(test_kcompletion test.cpp)
target_link_libraries(test_kcompletion KF6::Completion)

enable_testing()
add_test(NAME test_kcompletion COMMAND test_kcompletion)
