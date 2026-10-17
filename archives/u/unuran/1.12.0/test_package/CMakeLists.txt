cmake_minimum_required(VERSION 3.15)
project(unuran_test_package C)

find_package(unuran REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_unuran test_unuran.c)
target_link_libraries(test_unuran PRIVATE unuran::unuran Threads::Threads)
set_target_properties(test_unuran PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON)
