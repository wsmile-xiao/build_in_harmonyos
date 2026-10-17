cmake_minimum_required(VERSION 3.15)
project(test_explain C)

find_package(libexplain REQUIRED CONFIG)

add_executable(test_explain test_explain.c)
target_link_libraries(test_explain PRIVATE libexplain::libexplain)

enable_testing()
add_test(NAME libexplain_consumer COMMAND test_explain)
