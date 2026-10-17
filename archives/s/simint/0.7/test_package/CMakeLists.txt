cmake_minimum_required(VERSION 3.15)
project(test_simint C)

find_package(simint REQUIRED CONFIG)

add_executable(test_simint test.c)
target_link_libraries(test_simint PRIVATE simint::simint)
# math lib for OHOS/Linux
if(UNIX)
    target_link_libraries(test_simint PRIVATE m)
endif()
