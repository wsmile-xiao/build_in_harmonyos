cmake_minimum_required(VERSION 3.15)
project(kconfig_frontends_consumer C)

find_package(kconfig-parser CONFIG REQUIRED)

add_executable(kconfig_parser_consumer src/test_parser.c)
target_link_libraries(kconfig_parser_consumer PRIVATE kconfig-parser::kconfig-parser)
