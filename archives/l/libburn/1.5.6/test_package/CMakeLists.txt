cmake_minimum_required(VERSION 3.15)
project(libburn_test C)

find_package(libburn CONFIG REQUIRED)

add_executable(libburn_smoke main.c)
target_link_libraries(libburn_smoke PRIVATE libburn::libburn)

enable_testing()
add_test(NAME libburn_smoke COMMAND libburn_smoke)
