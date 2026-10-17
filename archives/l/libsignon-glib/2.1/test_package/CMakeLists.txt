cmake_minimum_required(VERSION 3.15)
project(test_libsignon-glib C)

# Find the package via Conan-generated PkgConfigDeps
find_package(PkgConfig REQUIRED)
pkg_check_modules(SIGNON_GLIB REQUIRED IMPORTED_TARGET libsignon-glib)

add_executable(test_libsignon-glib test.c)
target_link_libraries(test_libsignon-glib PkgConfig::SIGNON_GLIB)

enable_testing()
add_test(NAME test_libsignon-glib COMMAND test_libsignon-glib)
