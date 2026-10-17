cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(libcap-ng REQUIRED)

add_executable(${PROJECT_NAME} test.c)
target_link_libraries(${PROJECT_NAME} libcap-ng::libcap-ng)

enable_testing()
add_test(NAME ${PROJECT_NAME} COMMAND ${PROJECT_NAME})
