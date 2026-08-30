cmake_minimum_required(VERSION 3.15)
project(libxcvt_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

find_package(libxcvt CONFIG REQUIRED)

add_executable(libxcvt_api_surface api_surface.c)
target_compile_options(libxcvt_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxcvt_api_surface PRIVATE libxcvt::libxcvt)

add_executable(libxcvt_version_contract version_contract.c)
target_compile_options(libxcvt_version_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxcvt_version_contract PRIVATE libxcvt::libxcvt)
