cmake_minimum_required(VERSION 3.15)
project(libmarpa_test LANGUAGES C)

find_package(libmarpa CONFIG REQUIRED)

add_executable(libmarpa_test test.c)
target_link_libraries(libmarpa_test PRIVATE libmarpa::libmarpa)

enable_testing()
add_test(NAME libmarpa_test COMMAND libmarpa_test)
