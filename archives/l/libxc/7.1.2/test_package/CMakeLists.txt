cmake_minimum_required(VERSION 3.24)
project(test_libxc LANGUAGES C Fortran)

find_package(Libxc CONFIG REQUIRED COMPONENTS Fortran)

add_executable(test_libxc_c test.c)
target_link_libraries(test_libxc_c PRIVATE Libxc::xc)

add_executable(test_libxc_fortran_kxc test_kxc.f90)
target_link_libraries(test_libxc_fortran_kxc PRIVATE Libxc::xcf03)
