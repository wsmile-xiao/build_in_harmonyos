cmake_minimum_required(VERSION 3.15)
project(lbt_test_package C)

# test_consumer links the conan package's shared lib; at runtime the
# conanrun environment (LD_LIBRARY_PATH) resolves libblastrampoline.so.5.
find_package(libblastrampoline REQUIRED)
# CMakeDeps models the package as an INTERFACE IMPORTED target with no
# IMPORTED_LOCATION of its own; the real library file sits on the
# CONAN_LIB::* micro-targets it links, each wrapped in a
# $<$<CONFIG:..>:..> generator expression and carrying a config-suffixed
# IMPORTED_LOCATION_<CONFIG>. Resolve that location so the ctest wrapper
# can point LD_LIBRARY_PATH at the package lib dir (the OHOS clang embeds
# no rpath when linking by file path).
get_target_property(_lbt_link_libs libblastrampoline::libblastrampoline INTERFACE_LINK_LIBRARIES)
string(TOUPPER "${CMAKE_BUILD_TYPE}" _lbt_cfg)
set(_lbt_dir "")
foreach(_entry IN LISTS _lbt_link_libs)
    string(REGEX REPLACE "^\\$<\\$<CONFIG:[^>]*>:([^>]*)>$" "\\1" _entry "${_entry}")
    if(NOT TARGET "${_entry}")
        continue()
    endif()
    get_target_property(_lbt_loc "${_entry}" "IMPORTED_LOCATION_${_lbt_cfg}")
    if(NOT _lbt_loc)
        get_target_property(_lbt_loc "${_entry}" IMPORTED_LOCATION)
    endif()
    if(_lbt_loc)
        get_filename_component(_lbt_dir "${_lbt_loc}" DIRECTORY)
        break()
    endif()
endforeach()
if(NOT _lbt_dir)
    message(FATAL_ERROR
        "could not resolve the packaged libblastrampoline library directory "
        "(no CONAN_LIB::* micro-target with a location was linked)")
endif()
find_package(Threads REQUIRED)

# Three controlled fake BLAS backends (see comments in each .c file):
#  - fakeblas_lp64:            LP64 interface, suffix ""
#  - fakeblas_ilp64:           ILP64 interface, suffix "64_"
#  - fakeblas_ilp64_nosuffix:  ILP64 interface, suffix "" (conflict probe)
foreach(backend fakeblas_lp64 fakeblas_ilp64 fakeblas_ilp64_nosuffix)
    add_library(${backend} MODULE ${backend}.c)
    set_target_properties(${backend} PROPERTIES PREFIX "")
    target_link_libraries(${backend} PRIVATE ${CMAKE_DL_LIBS})
    # must be loadable via dlopen from the test binary's directory
    set_target_properties(${backend} PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/backends)
endforeach()

# The package's per-interface header dirs (include/libblastrampoline/{LP64,ILP64})
# are NOT added as include dirs: test_consumer.c declares the Fortran BLAS
# prototypes itself (the bundled LP64 openblas_config.h carries an upstream
# USE64BITINT quirk, see the comment in test_consumer.c). Only the package
# root (for libblastrampoline.h) is on the include path — via the imported
# target's INTERFACE_INCLUDE_DIRECTORIES.
add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer
    PRIVATE libblastrampoline::libblastrampoline ${CMAKE_DL_LIBS})

# The conanfile runs test_consumer directly (env=conanrun provides
# LD_LIBRARY_PATH for the packaged libblastrampoline.so.5); also register
# it with ctest, with a PATH/LD_LIBRARY_PATH wrapper for standalone use.
enable_testing()
add_test(NAME consumer
    COMMAND ${CMAKE_COMMAND}
        -DTEST_BIN=$<TARGET_FILE:test_consumer>
        -DBACKEND_DIR=${CMAKE_BINARY_DIR}/backends
        -DLBT_DIR=${_lbt_dir}
        -P ${CMAKE_CURRENT_SOURCE_DIR}/run_consumer.cmake)
