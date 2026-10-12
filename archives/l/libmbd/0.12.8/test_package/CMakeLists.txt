cmake_minimum_required(VERSION 3.15)
project(libmbd_consumer Fortran)

find_package(mbd CONFIG REQUIRED)

add_executable(test_mbd test_mbd.f90)
target_link_libraries(test_mbd PRIVATE Mbd::mbd)
