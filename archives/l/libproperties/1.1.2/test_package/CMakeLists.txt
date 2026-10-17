cmake_minimum_required(VERSION 3.15)
project(test_libproperties C)

# Find the package via Conan-generated CMakeDeps
find_package(libproperties REQUIRED)

# Layer-2 consumer test: real link against the installed package + public header.
add_executable(test_libproperties_api test_api.c)
target_link_libraries(test_libproperties_api libproperties::libproperties)

# HarmonyOS-specific guard: loads the installed shared object by its bare
# versioned soname, which only exists when the recipe injects
# CMAKE_SHARED_LIBRARY_SONAME_C_FLAG (see ../../conanfile.py).
# dlopen/dlsym live in libc on musl; CMAKE_DL_LIBS is empty there, so guard the
# link line (target_link_libraries() rejects an empty item list).
add_executable(test_libproperties_soname test_soname.c)
if(CMAKE_DL_LIBS)
    target_link_libraries(test_libproperties_soname ${CMAKE_DL_LIBS})
endif()
