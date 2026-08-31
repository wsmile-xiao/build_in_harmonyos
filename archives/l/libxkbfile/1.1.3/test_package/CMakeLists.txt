cmake_minimum_required(VERSION 3.15)
project(libxkbfile_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# XKBfile.h pulls XkbDescPtr from <X11/extensions/XKBstr.h>; the
# xorgproto/2025.1 dependency supplies it transitively.
find_package(libxkbfile CONFIG REQUIRED)

add_executable(libxkbfile_api_surface api_surface.c)
target_compile_options(libxkbfile_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxkbfile_api_surface PRIVATE libxkbfile::libxkbfile)

add_executable(libxkbfile_version_contract version_contract.c)
target_compile_options(libxkbfile_version_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxkbfile_version_contract PRIVATE libxkbfile::libxkbfile)
