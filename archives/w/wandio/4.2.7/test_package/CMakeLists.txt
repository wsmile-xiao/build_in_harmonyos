cmake_minimum_required(VERSION 3.15)
project(wandio_test LANGUAGES C)

find_package(wandio CONFIG REQUIRED)

add_executable(test_wandio test_wandio.c)
target_link_libraries(test_wandio PRIVATE wandio::wandio)
