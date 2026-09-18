cmake_minimum_required(VERSION 3.15)
project(libkibi_consumer C)

find_package(libkibi REQUIRED)

add_executable(libkibi_consumer test_package.c)
target_link_libraries(libkibi_consumer libkibi::libkibi)

enable_testing()
add_test(NAME libkibi_consumer COMMAND libkibi_consumer)
