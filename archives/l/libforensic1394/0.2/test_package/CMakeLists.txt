cmake_minimum_required(VERSION 3.15)
project(libforensic1394_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libforensic1394 CONFIG REQUIRED)

add_executable(forensic1394_api_surface api_surface.c)
target_compile_options(forensic1394_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(forensic1394_api_surface
                      PRIVATE libforensic1394::libforensic1394)

add_executable(forensic1394_bus_lifecycle bus_lifecycle.c)
target_compile_options(forensic1394_bus_lifecycle PRIVATE -Wall -Wextra -Werror)
target_link_libraries(forensic1394_bus_lifecycle
                      PRIVATE libforensic1394::libforensic1394)
