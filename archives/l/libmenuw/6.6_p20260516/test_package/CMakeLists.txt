cmake_minimum_required(VERSION 3.16)
project(libmenuw_consumer_tests LANGUAGES C)

find_package(libmenuw CONFIG REQUIRED)

add_executable(test_menu_consumer src/test_menu_consumer.c)
target_compile_definitions(test_menu_consumer PRIVATE _XOPEN_SOURCE_EXTENDED=1)
target_link_libraries(test_menu_consumer PRIVATE libmenuw::libmenuw)
