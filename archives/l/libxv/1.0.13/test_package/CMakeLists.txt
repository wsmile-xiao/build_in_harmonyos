cmake_minimum_required(VERSION 3.15)
project(libxv_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# Xvlib.h is not self-contained (it only includes Xfuncproto.h/Xv.h/XShm.h);
# consumers must include Xlib.h first.  The libx11/6.4.0 dependency supplies
# Xlib.h, libxext/6.4.0 supplies XShm.h and extutil.h, and the
# xorgproto/2025.1 dependency supplies Xv.h.
find_package(libxv CONFIG REQUIRED)

add_executable(libxv_api_surface api_surface.c)
target_compile_options(libxv_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxv_api_surface PRIVATE libxv::libxv)

add_executable(libxv_version_contract version_contract.c)
target_compile_options(libxv_version_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxv_version_contract PRIVATE libxv::libxv)
