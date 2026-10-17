cmake_minimum_required(VERSION 3.15)
project(test_traildb C)

find_package(traildb REQUIRED)

add_executable(test_traildb test_traildb.c)
target_link_libraries(test_traildb traildb::traildb)

enable_testing()
add_test(NAME test_traildb COMMAND test_traildb)
