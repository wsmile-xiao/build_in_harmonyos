cmake_minimum_required(VERSION 3.15)
project(test_slp LANGUAGES C)

find_package(openslp CONFIG REQUIRED)

set(CASES
    case_parse_basic
    case_parse_noport
    case_parse_ipv6
    case_parse_error
    case_escape
    case_openclose
    case_property)

foreach(c ${CASES})
    add_executable(${c} ${c}.c)
    target_link_libraries(${c} PRIVATE openslp::openslp)
endforeach()
