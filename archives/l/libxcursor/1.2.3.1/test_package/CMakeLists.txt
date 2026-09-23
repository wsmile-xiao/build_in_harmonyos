cmake_minimum_required(VERSION 3.20)
project(libxcursor_test_package C)

set(CMAKE_C_EXTENSIONS ON)

find_package(libxcursor CONFIG REQUIRED)

add_executable(libxcursor_api_surface api_surface.c)
target_link_libraries(libxcursor_api_surface PRIVATE libxcursor::libxcursor)
target_compile_options(libxcursor_api_surface PRIVATE -Werror)

add_executable(libxcursor_version_contract version_contract.c)
target_link_libraries(libxcursor_version_contract PRIVATE libxcursor::libxcursor)
target_compile_options(libxcursor_version_contract PRIVATE -Werror)
