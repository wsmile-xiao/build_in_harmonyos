cmake_minimum_required(VERSION 3.15)
project(test_vgmplay C)

find_package(vgmplay REQUIRED)

# vgmplay is an application package: CMakeDeps exposes the packaged bin dir
# via vgmplay_BIN_DIRS_RELEASE (the imported target is INTERFACE-only and
# carries no IMPORTED_LOCATION). Pass the bin dir to the consumer test so it
# can exec the packaged CLI by absolute path.
add_executable(test_vgmplay test.c)
add_test(NAME test_vgmplay COMMAND test_vgmplay "${vgmplay_BIN_DIRS_RELEASE}")

enable_testing()
