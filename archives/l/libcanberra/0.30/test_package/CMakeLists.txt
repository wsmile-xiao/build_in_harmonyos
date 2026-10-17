cmake_minimum_required(VERSION 3.20)
project(libcanberra_test_package C)

set(CMAKE_C_EXTENSIONS ON)

find_package(libcanberra CONFIG REQUIRED)

add_executable(libcanberra_api_surface api_surface.c)
target_link_libraries(libcanberra_api_surface PRIVATE libcanberra::libcanberra)
target_compile_options(libcanberra_api_surface PRIVATE -Werror)

add_executable(libcanberra_version_contract version_contract.c)
target_link_libraries(libcanberra_version_contract PRIVATE libcanberra::libcanberra)
target_compile_options(libcanberra_version_contract PRIVATE -Werror)
