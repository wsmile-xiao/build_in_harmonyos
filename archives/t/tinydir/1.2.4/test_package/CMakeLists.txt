cmake_minimum_required(VERSION 3.15)
project(test_tinydir_harmonyos C)

find_package(tinydir REQUIRED)

add_executable(test_tinydir_harmonyos test_tinydir_harmonyos.c)
target_link_libraries(test_tinydir_harmonyos PRIVATE tinydir::tinydir)
set_target_properties(test_tinydir_harmonyos PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_tinydir_harmonyos COMMAND test_tinydir_harmonyos)