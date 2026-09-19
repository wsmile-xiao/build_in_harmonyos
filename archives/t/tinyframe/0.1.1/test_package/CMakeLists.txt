cmake_minimum_required(VERSION 3.15)
project(tinyframe_test_package C)

find_package(tinyframe REQUIRED CONFIG)
enable_testing()

add_executable(tinyframe_tests tinyframe_tests.c)
target_link_libraries(tinyframe_tests PRIVATE tinyframe::tinyframe)

foreach(case_name IN ITEMS
        frame_size header_endian ready_control start_control frame_roundtrip
        stop_control finish_control partial_input invalid_field)
    add_test(NAME "tinyframe.${case_name}"
             COMMAND tinyframe_tests "${case_name}")
    set_tests_properties("tinyframe.${case_name}" PROPERTIES TIMEOUT 10)
endforeach()

add_executable(tinyframe_ohos_test ohos_platform_test.c)
target_link_libraries(tinyframe_ohos_test PRIVATE tinyframe::tinyframe)
add_test(NAME tinyframe.harmonyos_platform COMMAND tinyframe_ohos_test)
set_tests_properties(tinyframe.harmonyos_platform PROPERTIES TIMEOUT 10)
