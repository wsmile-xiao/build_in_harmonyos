cmake_minimum_required(VERSION 3.15)
project(test_glibmm CXX)

if(DEFINED OHOS_SYSTEM_INCLUDE_DIRS)
    include_directories(${OHOS_SYSTEM_INCLUDE_DIRS})
endif()
if(DEFINED OHOS_SYSTEM_LIB_DIRS)
    link_directories(${OHOS_SYSTEM_LIB_DIRS})
endif()

find_package(PkgConfig REQUIRED)
pkg_check_modules(GLIBMM REQUIRED IMPORTED_TARGET glibmm-2.4)

get_target_property(_glibmm_incs PkgConfig::GLIBMM INTERFACE_INCLUDE_DIRECTORIES)
if(_glibmm_incs)
    set(_glibmm_clean_incs "")
    foreach(_inc IN LISTS _glibmm_incs)
        if(EXISTS "${_inc}")
            list(APPEND _glibmm_clean_incs "${_inc}")
        endif()
    endforeach()
    set_target_properties(PkgConfig::GLIBMM PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "${_glibmm_clean_incs}")
endif()

add_executable(test_glibmm test_glibmm.cpp)
target_link_libraries(test_glibmm PRIVATE PkgConfig::GLIBMM)
target_compile_features(test_glibmm PRIVATE cxx_std_17)
