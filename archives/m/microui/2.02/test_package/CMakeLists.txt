cmake_minimum_required(VERSION 3.15)
project(test_microui C)

find_package(microui REQUIRED)

add_executable(test_microui test.c)
target_link_libraries(test_microui PRIVATE microui::microui)

enable_testing()
add_test(NAME test_microui COMMAND test_microui)
