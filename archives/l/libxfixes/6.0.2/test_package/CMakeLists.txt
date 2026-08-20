cmake_minimum_required(VERSION 3.15)
project(libxfixes_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

find_package(libxfixes CONFIG REQUIRED)

add_executable(libxfixes_api_surface api_surface.c)
target_compile_options(libxfixes_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxfixes_api_surface PRIVATE libxfixes::libxfixes)

add_executable(libxfixes_version_contract version_contract.c)
target_compile_options(libxfixes_version_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxfixes_version_contract PRIVATE libxfixes::libxfixes)
