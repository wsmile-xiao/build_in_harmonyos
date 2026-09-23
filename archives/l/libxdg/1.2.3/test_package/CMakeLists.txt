cmake_minimum_required(VERSION 3.15)
project(libxdg_test_package C)

find_package(libxdg REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_libxdg test_libxdg.c)
target_link_libraries(test_libxdg PRIVATE libxdg::libxdg Threads::Threads)
set_target_properties(test_libxdg PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON)
