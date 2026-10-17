cmake_minimum_required(VERSION 3.15)
project(test_libhinawa C)

find_package(libhinawa CONFIG REQUIRED)

add_executable(test_libhinawa test_libhinawa.c)
target_link_libraries(test_libhinawa PRIVATE libhinawa::libhinawa)

enable_testing()
set(LIBHINAWA_TEST_NAMES
    fw_node
    fw_req
    fw_resp
    fw_fcp
    cycle_time
    hinawa_enums
    hinawa_functions
    ohos_aarch64_abi)

list(LENGTH LIBHINAWA_TEST_NAMES test_count)
math(EXPR test_last "${test_count} - 1")
foreach(test_index RANGE 0 ${test_last})
    list(GET LIBHINAWA_TEST_NAMES ${test_index} test_name)
    math(EXPR test_argument "${test_index} + 1")
    add_test(NAME ${test_name} COMMAND test_libhinawa ${test_argument})
endforeach()
