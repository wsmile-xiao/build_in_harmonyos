cmake_minimum_required(VERSION 3.15)
project(test_gspell C)

find_package(PkgConfig REQUIRED)
# gspell-1.pc carries the whole public chain (gio-2.0, gtk+-3.0, enchant-2),
# so pkg-config resolves the transitive include/lib flags for us.
pkg_check_modules(GSPELL REQUIRED gspell-1)

add_executable(test_gspell test_gspell.c)

target_include_directories(test_gspell PRIVATE ${GSPELL_INCLUDE_DIRS})
target_compile_options(test_gspell PRIVATE ${GSPELL_CFLAGS_OTHER})
target_link_directories(test_gspell PRIVATE ${GSPELL_LIBRARY_DIRS})
target_link_options(test_gspell PRIVATE ${GSPELL_LDFLAGS_OTHER})
target_link_libraries(test_gspell PRIVATE ${GSPELL_LIBRARIES})

# libgspell-1 statically absorbs ICU (a C++ archive on this platform), so the
# C++ runtime must be resolvable for the consumer link as well.
target_link_libraries(test_gspell PRIVATE c++)
