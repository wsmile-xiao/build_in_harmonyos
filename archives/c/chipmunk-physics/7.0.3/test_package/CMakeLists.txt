cmake_minimum_required(VERSION 3.15)
project(test_chipmunk C)

find_package(chipmunk-physics REQUIRED)

add_executable(test_chipmunk test.c)
target_link_libraries(test_chipmunk chipmunk-physics::chipmunk-physics)

enable_testing()
add_test(NAME test_chipmunk COMMAND test_chipmunk)
