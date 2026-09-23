cmake_minimum_required(VERSION 3.15)
project(c-stdaux_consumer_test C)

find_package(c-stdaux CONFIG REQUIRED)

add_executable(c-stdaux_test c-stdaux_test.c)
target_link_libraries(c-stdaux_test PRIVATE c-stdaux::c-stdaux)

enable_testing()
add_test(NAME c-stdaux_test COMMAND c-stdaux_test)
