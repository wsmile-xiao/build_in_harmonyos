cmake_minimum_required(VERSION 3.15)
project(test_libpri C)

# libpri::libpri comes from the Conan-generated CMakeDeps files, i.e. it points
# at the library this package installs (include/ + lib/).
find_package(libpri REQUIRED)

add_executable(test_libpri test_libpri.c)
target_link_libraries(test_libpri libpri::libpri)
