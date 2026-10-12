cmake_minimum_required(VERSION 3.15)
project(test_pffft C)

find_package(pffft CONFIG REQUIRED)

add_executable(test_pffft test_pffft.c)
if(TARGET pffft::pffft)
    target_link_libraries(test_pffft PRIVATE pffft::pffft)
else()
    target_link_libraries(test_pffft PRIVATE pffft)
endif()
