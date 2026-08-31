cmake_minimum_required(VERSION 3.15)
project(libxres_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# XRes.h is not self-contained (it only pulls Xfuncproto.h); consumers must
# include Xlib.h first.  The libx11/6.4.0 dependency supplies Xlib.h and the
# xorgproto/2025.1 dependency supplies XResproto.h.
find_package(libxres CONFIG REQUIRED)

add_executable(libxres_api_surface api_surface.c)
target_compile_options(libxres_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxres_api_surface PRIVATE libxres::libxres)

add_executable(libxres_version_contract version_contract.c)
target_compile_options(libxres_version_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxres_version_contract PRIVATE libxres::libxres)
