cmake_minimum_required(VERSION 3.15)
project(libsepol_test LANGUAGES C)

enable_testing()

find_package(PkgConfig QUIET)

# Primary: Conan 生成的 libsepol 包
find_package(libsepol REQUIRED)

add_executable(test_sepol test.c)
target_link_libraries(test_sepol PRIVATE libsepol::libsepol)

# 备选：pkg-config 路径（若 find_package 失败时使用）
if(PkgConfig_FOUND AND NOT TARGET libsepol::libsepol)
    pkg_check_modules(SEPOL libsepol)
    if(SEPOL_FOUND)
        target_include_directories(test_sepol PRIVATE ${SEPOL_INCLUDE_DIRS})
        target_link_directories(test_sepol PRIVATE ${SEPOL_LIBRARY_DIRS})
        target_link_libraries(test_sepol ${SEPOL_LIBRARIES})
    endif()
endif()

# Ensure the test runs as part of the build
add_test(NAME test_sepol COMMAND test_sepol)