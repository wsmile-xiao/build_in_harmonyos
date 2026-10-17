cmake_minimum_required(VERSION 3.15)
project(test_libuemf C)

find_package(libuemf REQUIRED)

add_executable(test_libuemf test_libuemf_api.c)
target_link_libraries(test_libuemf libuemf::libuemf)

enable_testing()
add_test(NAME test_libuemf COMMAND test_libuemf)
