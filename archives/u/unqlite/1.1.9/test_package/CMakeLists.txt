cmake_minimum_required(VERSION 3.15)
project(test_unqlite C)

find_package(unqlite CONFIG REQUIRED)

add_executable(test_unqlite test_unqlite.c)
target_link_libraries(test_unqlite PRIVATE unqlite::unqlite)
set_property(TARGET test_unqlite PROPERTY C_STANDARD 99)
