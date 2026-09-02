cmake_minimum_required(VERSION 3.15)
project(test_libxfixes C)

# The OHOS user toolchain (ohos.toolchain.cmake) sets
# CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY, which stops find_package() from
# searching CMAKE_PREFIX_PATH (where conan 2's CMakeDeps generator writes
# libxfixes-config.cmake).  Override to BOTH so the conan generators folder is
# searched alongside the OHOS SDK tree.
if(DEFINED CMAKE_FIND_ROOT_PATH_MODE_PACKAGE)
    set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
endif()

find_package(libxfixes REQUIRED)
find_package(libx11 REQUIRED)
find_package(xorgproto REQUIRED)

add_executable(test_libxfixes test.c)
target_link_libraries(test_libxfixes PRIVATE
    libxfixes::libxfixes
    libx11::libx11
    xorgproto::xorgproto
)

enable_testing()
add_test(NAME test_libxfixes COMMAND test_libxfixes)
