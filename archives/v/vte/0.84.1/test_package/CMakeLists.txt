cmake_minimum_required(VERSION 3.15)
project(test_vte C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(VTE REQUIRED IMPORTED_TARGET vte-2.91-gtk4)

add_executable(test_vte test.c)
target_link_libraries(test_vte PkgConfig::VTE)

if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
    target_link_options(test_vte PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
endif()

enable_testing()
add_test(NAME test_vte COMMAND $<TARGET_FILE:test_vte>)
