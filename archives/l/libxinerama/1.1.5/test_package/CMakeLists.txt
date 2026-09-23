cmake_minimum_required(VERSION 3.15)
project(libxinerama_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

find_package(libxinerama CONFIG REQUIRED)

add_executable(libxinerama_api_surface api_surface.c)
target_compile_options(libxinerama_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxinerama_api_surface PRIVATE libxinerama::libxinerama)

add_executable(libxinerama_version_contract version_contract.c)
target_compile_options(libxinerama_version_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxinerama_version_contract PRIVATE libxinerama::libxinerama)
