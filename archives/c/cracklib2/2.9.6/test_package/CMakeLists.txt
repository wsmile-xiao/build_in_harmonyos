cmake_minimum_required(VERSION 3.15)
project(test_cracklib2 C)

find_package(cracklib2 REQUIRED)

add_executable(test_cracklib2 test.c)
target_link_libraries(test_cracklib2 cracklib2::cracklib2)

enable_testing()
add_test(NAME test_cracklib2 COMMAND test_cracklib2 ${TEST_DICT_PREFIX})
