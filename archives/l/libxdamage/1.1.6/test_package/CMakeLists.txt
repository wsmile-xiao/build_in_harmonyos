cmake_minimum_required(VERSION 3.15)
project(libxdamage_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

find_package(libxdamage CONFIG REQUIRED)

add_executable(libxdamage_api_surface api_surface.c)
target_compile_options(libxdamage_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxdamage_api_surface PRIVATE libxdamage::libxdamage)

add_executable(libxdamage_version_contract version_contract.c)
target_compile_options(libxdamage_version_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxdamage_version_contract PRIVATE libxdamage::libxdamage)
