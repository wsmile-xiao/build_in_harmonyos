cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(libmagic REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE libmagic::libmagic)
target_include_directories(test_package PRIVATE ${libmagic_INCLUDE_DIRS})

# 数据库：与头文件同前缀的 share/misc/magic.mgc（上游 pkgdatadir 约定）
get_filename_component(_prefix "${libmagic_INCLUDE_DIRS}" DIRECTORY)
target_compile_definitions(test_package PRIVATE
    MAGIC_DB_PATH="${_prefix}/share/misc/magic.mgc")

enable_testing()
add_test(NAME test_package COMMAND test_package)
