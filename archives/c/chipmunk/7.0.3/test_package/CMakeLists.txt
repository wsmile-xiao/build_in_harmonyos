cmake_minimum_required(VERSION 3.15)
project(test_chipmunk CXX)

find_package(chipmunk REQUIRED)

add_executable(test_chipmunk test_chipmunk.cpp)
target_link_libraries(test_chipmunk PRIVATE chipmunk::chipmunk)

enable_testing()
add_test(NAME chipmunk_consumer COMMAND test_chipmunk)
