cmake_minimum_required(VERSION 3.15)
project(test_libtins CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libtins CONFIG REQUIRED)

if(TARGET tins)
    set(LIBTINS_LINK_TARGET tins)
elseif(TARGET libtins::tins)
    set(LIBTINS_LINK_TARGET libtins::tins)
else()
    message(FATAL_ERROR "libtins CMake target not found in the installed package")
endif()

add_executable(test_libtins test_libtins.cpp)
target_link_libraries(test_libtins PRIVATE ${LIBTINS_LINK_TARGET})
