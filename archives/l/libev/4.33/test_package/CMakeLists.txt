cmake_minimum_required(VERSION 3.15)
project(test_libev C)

# Find the package via Conan-generated CMakeDeps
find_package(libev REQUIRED)

add_executable(test_libev test.c)
target_link_libraries(test_libev libev::libev)

add_executable(test_libev_unit unit_test.c)
target_link_libraries(test_libev_unit libev::libev)

enable_testing()
add_test(NAME test_libev COMMAND test_libev)
add_test(NAME libev_unit_version COMMAND test_libev_unit version)
add_test(NAME libev_unit_loop_userdata COMMAND test_libev_unit loop_userdata)
add_test(NAME libev_unit_timer_once COMMAND test_libev_unit timer_once)
