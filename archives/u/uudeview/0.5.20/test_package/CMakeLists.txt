cmake_minimum_required(VERSION 3.15)
project(test_uudeview C)

find_package(uudeview REQUIRED)

add_executable(test_uudeview test.c)
target_link_libraries(test_uudeview uudeview::uudeview)

enable_testing()
add_test(NAME test_uudeview COMMAND test_uudeview)
