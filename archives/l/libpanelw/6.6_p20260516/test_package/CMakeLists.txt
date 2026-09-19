cmake_minimum_required(VERSION 3.16)
project(libpanelw_consumer_tests LANGUAGES C)

find_package(libpanelw CONFIG REQUIRED)

add_executable(test_panel_consumer src/test_panel_consumer.c)
target_compile_definitions(test_panel_consumer PRIVATE _XOPEN_SOURCE_EXTENDED=1)
target_link_libraries(test_panel_consumer PRIVATE libpanelw::libpanelw)
