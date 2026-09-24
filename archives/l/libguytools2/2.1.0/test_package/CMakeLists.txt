cmake_minimum_required(VERSION 3.15)
project(test_libguytools2 CXX)

# The library is a C++ library that exposes QString in its public API
# (toolsysinfo.h), so the test package is built as C++ and links Qt5Core.
# qt5-qtbase's CMakeDeps package file declares the Qt5::Core component.
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Version the tested package must report at run time.  test_package/conanfile.py
# passes it from the tested reference, so the functional test fails when a
# stale or mis-versioned library ends up in the package.
if(NOT DEFINED LIBGUYTOOLS2_TESTED_VERSION)
  message(FATAL_ERROR
          "LIBGUYTOOLS2_TESTED_VERSION is not set - configure with "
          "-DLIBGUYTOOLS2_TESTED_VERSION=<version>")
endif()

# Find the package via Conan-generated CMakeDeps
find_package(libguytools2 REQUIRED)

add_executable(test_libguytools2 test_libguytools2.cpp)
target_link_libraries(test_libguytools2 PRIVATE libguytools2::libguytools2 Qt5::Core)
target_compile_definitions(test_libguytools2 PRIVATE
                           EXPECTED_VERSION="${LIBGUYTOOLS2_TESTED_VERSION}")

enable_testing()
add_test(NAME test_libguytools2 COMMAND test_libguytools2)
