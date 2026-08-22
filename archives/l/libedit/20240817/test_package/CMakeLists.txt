cmake_minimum_required(VERSION 3.15)
project(test_libedit C)

# Find the package via Conan-generated CMakeDeps
find_package(libedit REQUIRED)

# ncurses is a transitive runtime dependency of libedit.
# The test binary links against libedit which already brings in ncurses.
# Header search is optional — test code does not directly include curses.h.
find_library(NCURSES_LIB NAMES ncursesw ncurses
  HINTS "$ENV{NCURSES_ROOT}/lib" "$ENV{NCURSES_PREFIX}/lib")
if(NOT NCURSES_LIB)
  message(STATUS "ncurses library not found via NCURSES_ROOT — trying default link")
  set(NCURSES_LIB ncursesw)
endif()

find_path(NCURSES_INCLUDE_DIR curses.h
  HINTS "$ENV{NCURSES_ROOT}/include" "$ENV{NCURSES_PREFIX}/include"
    "$ENV{NCURSES_INCLUDE}")
if(NCURSES_INCLUDE_DIR)
  message(STATUS "ncurses header found: ${NCURSES_INCLUDE_DIR}")
else()
  message(STATUS "ncurses header not found — test does not require curses.h directly")
endif()

add_executable(test_libedit test_libedit.c)
target_link_libraries(test_libedit libedit::libedit ${NCURSES_LIB})
if(NCURSES_INCLUDE_DIR)
  target_include_directories(test_libedit PRIVATE ${NCURSES_INCLUDE_DIR})
endif()

enable_testing()
add_test(NAME test_libedit COMMAND test_libedit)