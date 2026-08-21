cmake_minimum_required(VERSION 3.15)
project(libxrender_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libxrender CONFIG REQUIRED)

add_executable(libxrender_api_surface api_surface.c)
target_compile_options(libxrender_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxrender_api_surface PRIVATE libxrender::libxrender)

add_executable(libxrender_color_contract color_contract.c)
target_compile_options(libxrender_color_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxrender_color_contract PRIVATE libxrender::libxrender)
