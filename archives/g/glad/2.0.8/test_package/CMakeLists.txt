cmake_minimum_required(VERSION 3.15)
project(test_glad C)

find_package(glad REQUIRED)

add_executable(test_glad test_glad.c)
target_link_libraries(test_glad glad::glad)

add_executable(harmonyos_specific_test harmonyos_specific_test.c)
target_link_libraries(harmonyos_specific_test glad::glad)

enable_testing()
add_test(NAME test_glad COMMAND test_glad)
add_test(NAME harmonyos_specific_test COMMAND harmonyos_specific_test)
