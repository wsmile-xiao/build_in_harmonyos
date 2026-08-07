cmake_minimum_required(VERSION 3.15)
project(aalib_test C)

find_package(aalib CONFIG REQUIRED)

add_executable(aalib_smoke main.c)
target_link_libraries(aalib_smoke PRIVATE aalib::aalib)

enable_testing()
add_test(NAME aalib_smoke COMMAND aalib_smoke)