cmake_minimum_required(VERSION 3.15)
project(test_mimick C)

find_package(mimick CONFIG REQUIRED)

add_library(foo SHARED libfoo.c)
add_executable(test_mimick test.c)
target_link_libraries(test_mimick PRIVATE mimick::mimick foo)

if (NOT MSVC)
    set_source_files_properties(test.c PROPERTIES COMPILE_FLAGS "-O0")
endif ()

enable_testing()
add_test(NAME test_mimick COMMAND test_mimick)
set_tests_properties(test_mimick PROPERTIES
    ENVIRONMENT "LD_LIBRARY_PATH=$<TARGET_FILE_DIR:foo>")
