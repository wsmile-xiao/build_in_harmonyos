cmake_minimum_required(VERSION 3.15)
project(test_ncurses C)

# Find the package via Conan-generated CMakeDeps
find_package(ncurses REQUIRED)

add_executable(test_ncurses_smoke test_ncurses_smoke.c)
target_link_libraries(test_ncurses_smoke ncurses::ncurses)

enable_testing()
add_test(NAME test_ncurses_smoke COMMAND test_ncurses_smoke)
