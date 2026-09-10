cmake_minimum_required(VERSION 3.15)
project(libxi_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# XInput2.h pulls <X11/extensions/Xfixes.h> for the PointerBarrier typedef;
# the vendored header is provided only for the consumer test build.
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

find_package(libxi CONFIG REQUIRED)

add_executable(libxi_api_surface api_surface.c)
target_compile_options(libxi_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxi_api_surface PRIVATE libxi::libxi)

add_executable(libxi_version_contract version_contract.c)
target_compile_options(libxi_version_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxi_version_contract PRIVATE libxi::libxi)
