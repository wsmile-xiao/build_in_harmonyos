cmake_minimum_required(VERSION 3.15)
project(test_libisofs C)

# HarmonyOS is unknown to CMake, so find_library has no default library
# suffixes/prefixes; declare them explicitly so CMakeDeps can locate the
# static archive libisofs.a in the package lib dir.
if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")
    set(CMAKE_FIND_LIBRARY_SUFFIXES ".so" ".a" )
    set(CMAKE_FIND_LIBRARY_PREFIXES "lib" "" )
endif()

# Find the package via Conan-generated CMakeDeps
find_package(libisofs REQUIRED)

add_executable(test_libisofs test.c)
target_link_libraries(test_libisofs libisofs::libisofs)

enable_testing()
add_test(NAME test_libisofs COMMAND test_libisofs)
