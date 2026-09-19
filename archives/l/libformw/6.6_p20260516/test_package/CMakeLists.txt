cmake_minimum_required(VERSION 3.15)
project(test_libformw C)

# Exercises the form library API in-process (no terminal required).
# form.h pulls in <curses.h> from the visible ncurses/6.6 dependency, which
# also validates the header chain; static linking resolves libformw.a against
# libncursesw.a from the parent package. CMakeDeps generates both targets;
# both are linked explicitly (libgmpxx same-source-sublibrary pattern), the
# recipe also declares cpp_info.requires so downstream targets propagate.
find_package(formw CONFIG REQUIRED)
find_package(ncurses CONFIG REQUIRED)

add_executable(test_form_api src/test_form_api.c)
target_link_libraries(test_form_api PRIVATE formw::formw ncurses::ncurses)
