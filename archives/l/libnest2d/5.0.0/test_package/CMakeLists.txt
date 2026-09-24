cmake_minimum_required(VERSION 3.20)
project(test_libnest2d CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Libnest2D REQUIRED)
find_package(Boost REQUIRED)
find_package(Armadillo REQUIRED)

add_executable(test_libnest2d test.cpp)
target_link_libraries(test_libnest2d PRIVATE Libnest2D::libnest2d)

# Vendored Clipper fallback: libnest2d header-only exposes Clipper symbols via
# static libpolyclipping.a installed to <package>/lib. The interface target
# should transitively link it, but for Conan header-library the libdirs/libs
# propagation may be incomplete. Explicitly locate and link the vendored
# library if not already transitively linked.
if(TARGET Libnest2D::libnest2d)
    get_target_property(_libnest_link Libnest2D::libnest2d INTERFACE_LINK_LIBRARIES)
    if(_libnest_link)
        string(FIND "${_libnest_link}" "polyclipping" _has_poly)
    else()
        set(_has_poly -1)
    endif()
    if(_has_poly EQUAL -1)
        find_library(POLYCLIPPING_LIB polyclipping
            PATHS ${Libnest2D_LIB_DIRS} ${CMAKE_PREFIX_PATH}
            PATH_SUFFIXES lib
            NO_DEFAULT_PATH)
        if(NOT POLYCLIPPING_LIB)
            find_library(POLYCLIPPING_LIB polyclipping)
        endif()
        if(POLYCLIPPING_LIB)
            target_link_libraries(test_libnest2d PRIVATE ${POLYCLIPPING_LIB})
            message(STATUS "Linking vendored polyclipping: ${POLYCLIPPING_LIB}")
        else()
            if(TARGET polyclipping)
                target_link_libraries(test_libnest2d PRIVATE polyclipping)
            elseif(TARGET clipper::clipper)
                target_link_libraries(test_libnest2d PRIVATE clipper::clipper)
            endif()
        endif()
    endif()
endif()
