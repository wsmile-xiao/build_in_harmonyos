cmake_minimum_required(VERSION 3.15)
project(test_libpg_query C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBPG_QUERY REQUIRED IMPORTED_TARGET libpg_query)

add_executable(test_libpg_query test_libpg_query.c)
target_link_libraries(test_libpg_query PkgConfig::LIBPG_QUERY)
