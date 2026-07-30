cmake_minimum_required(VERSION 3.15)
project(test_mpack C)

find_package(mpack-msgpack REQUIRED)

add_executable(test_mpack test.c)
target_link_libraries(test_mpack mpack-msgpack::mpack-msgpack)

enable_testing()
add_test(NAME test_mpack COMMAND test_mpack)
