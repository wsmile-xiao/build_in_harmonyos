cmake_minimum_required(VERSION 3.15)
project(opt_test LANGUAGES C)

find_package(opt CONFIG REQUIRED)
add_executable(test_opt test.c)
target_link_libraries(test_opt PRIVATE opt::opt)
