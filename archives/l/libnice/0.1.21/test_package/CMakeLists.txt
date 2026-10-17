cmake_minimum_required(VERSION 3.15)
project(libnice_consumer C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBNICE REQUIRED IMPORTED_TARGET nice)

add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer PRIVATE PkgConfig::LIBNICE)
