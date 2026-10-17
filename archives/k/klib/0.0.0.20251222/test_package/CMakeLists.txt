cmake_minimum_required(VERSION 3.15)
project(test_klib C)

find_package(klib CONFIG REQUIRED)

find_file(KLIB_KSTRING_SOURCE
    NAMES kstring.c
    PATHS ${klib_INCLUDE_DIRS}
    PATH_SUFFIXES klib
    NO_DEFAULT_PATH
    REQUIRED
)

add_executable(test_klib test_klib.c ${KLIB_KSTRING_SOURCE})
target_link_libraries(test_klib PRIVATE klib::klib)
set_property(TARGET test_klib PROPERTY C_STANDARD 99)
