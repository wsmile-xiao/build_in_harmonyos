cmake_minimum_required(VERSION 3.15)
project(test_libxdamage C)

# The OHOS user toolchain (ohos.toolchain.cmake) sets
# CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY, which stops find_package() from
# searching CMAKE_PREFIX_PATH (where conan 2's CMakeDeps generator writes
# libxdamage-config.cmake).  Override to BOTH so the conan generators folder is
# searched alongside the OHOS SDK tree.
if(DEFINED CMAKE_FIND_ROOT_PATH_MODE_PACKAGE)
    set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
endif()

find_package(libxdamage REQUIRED)
find_package(libx11 REQUIRED)
find_package(libxfixes REQUIRED)
find_package(xorgproto REQUIRED)

add_executable(test_libxdamage test.c)
target_link_libraries(test_libxdamage PRIVATE
    libxdamage::libxdamage
    libx11::libx11
    libxfixes::libxfixes
    xorgproto::xorgproto
)

enable_testing()
add_test(NAME test_libxdamage COMMAND test_libxdamage)
