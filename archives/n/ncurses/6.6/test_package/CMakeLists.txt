cmake_minimum_required(VERSION 3.16)
project(ncurses_consumer_tests LANGUAGES C)

set(CURSES_NEED_WIDE TRUE)
find_package(Curses REQUIRED)

add_executable(test_curses_module src/test_curses_module.c)
target_compile_definitions(test_curses_module PRIVATE _XOPEN_SOURCE_EXTENDED=1)
target_include_directories(test_curses_module PRIVATE ${CURSES_INCLUDE_DIRS})
target_link_libraries(test_curses_module PRIVATE ${CURSES_LIBRARIES})

find_package(ncurses CONFIG REQUIRED)

add_executable(test_ncurses_components src/test_ncurses_components.c)
target_compile_definitions(test_ncurses_components PRIVATE _XOPEN_SOURCE_EXTENDED=1)
target_link_libraries(test_ncurses_components PRIVATE ncurses::ncurses)
