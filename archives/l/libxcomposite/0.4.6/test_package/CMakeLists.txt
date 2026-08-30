cmake_minimum_required(VERSION 3.15)
project(libxcomposite_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# Xcomposite.h pulls <X11/extensions/Xfixes.h>; the libxfixes/6.1.0
# dependency supplies it transitively via the package's include dir.
find_package(libxcomposite CONFIG REQUIRED)

add_executable(libxcomposite_api_surface api_surface.c)
target_compile_options(libxcomposite_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxcomposite_api_surface PRIVATE libxcomposite::libxcomposite)

add_executable(libxcomposite_version_contract version_contract.c)
target_compile_options(libxcomposite_version_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxcomposite_version_contract PRIVATE libxcomposite::libxcomposite)
