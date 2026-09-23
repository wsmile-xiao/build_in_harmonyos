cmake_minimum_required(VERSION 3.15)
project(test_libfilteraudio C)

# libfilteraudio::libfilteraudio comes from the Conan-generated CMakeDeps files,
# i.e. it points at the library this package installs (include/ + lib/).
find_package(libfilteraudio REQUIRED)

add_executable(test_libfilteraudio test.c)
target_link_libraries(test_libfilteraudio libfilteraudio::libfilteraudio)
