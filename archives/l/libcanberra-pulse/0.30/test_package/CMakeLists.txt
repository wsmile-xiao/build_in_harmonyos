cmake_minimum_required(VERSION 3.20)
project(libcanberra_pulse_test_package C)

set(CMAKE_C_EXTENSIONS ON)

find_package(libcanberra CONFIG REQUIRED)

add_executable(libcanberra_api_surface api_surface.c)
target_link_libraries(libcanberra_api_surface PRIVATE libcanberra::libcanberra)
target_compile_options(libcanberra_api_surface PRIVATE -Werror)

add_executable(libcanberra_pulse_contract pulse_contract.c)
target_link_libraries(libcanberra_pulse_contract PRIVATE libcanberra::libcanberra)
target_compile_options(libcanberra_pulse_contract PRIVATE -Werror)
