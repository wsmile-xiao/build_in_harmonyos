cmake_minimum_required(VERSION 3.16)
project(test_dee C)

if(NOT DEFINED DEE_ROOT OR "${DEE_ROOT}" STREQUAL "")
  message(FATAL_ERROR "DEE_ROOT is required")
endif()

find_package(PkgConfig REQUIRED)
# dee's libdee-1.0.pc lives in the package; glib pc files come from PkgConfigDeps
set(ENV{PKG_CONFIG_PATH} "${DEE_ROOT}/lib/pkgconfig:${CMAKE_BINARY_DIR}/generators")
pkg_check_modules(DEE REQUIRED IMPORTED_TARGET libdee-1.0)

# dee headers install under include/dee-1.0/ (devel_headersdir); the installed
# .pc may not relocate includedir to the conan package folder, add it explicitly.
include_directories("${DEE_ROOT}/include/dee-1.0")

add_executable(test_dee test_dee.c)
target_link_libraries(test_dee PRIVATE PkgConfig::DEE)

enable_testing()
add_test(NAME test_dee COMMAND test_dee)
