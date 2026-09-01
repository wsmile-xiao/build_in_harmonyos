cmake_minimum_required(VERSION 3.16)
project(sdl2_net_test_package C)

find_package(SDL2 REQUIRED CONFIG)
find_package(SDL2_net REQUIRED CONFIG)

if(SDL2_NET_TEST_SHARED)
    set(SDL2_TARGET SDL2::SDL2)
    set(SDL2_NET_TARGET SDL2_net::SDL2_net)
else()
    set(SDL2_TARGET SDL2::SDL2-static)
    set(SDL2_NET_TARGET SDL2_net::SDL2_net-static)
endif()

function(assert_target_from_package target_name expected_root)
    if(NOT TARGET "${target_name}")
        message(FATAL_ERROR "Required imported target is missing: ${target_name}")
    endif()
    if(NOT IS_ABSOLUTE "${expected_root}")
        message(FATAL_ERROR "Expected package root is not absolute: ${expected_root}")
    endif()
    if(NOT IS_DIRECTORY "${expected_root}/include")
        message(FATAL_ERROR "Package include directory is missing: ${expected_root}/include")
    endif()
    if(NOT IS_DIRECTORY "${expected_root}/lib")
        message(FATAL_ERROR "Package library directory is missing: ${expected_root}/lib")
    endif()
endfunction()

assert_target_from_package("${SDL2_TARGET}" "${EXPECTED_SDL2_ROOT}")
assert_target_from_package("${SDL2_NET_TARGET}" "${EXPECTED_SDL2_NET_ROOT}")

set(TEST_PROGRAMS
    test_upstream_cmake_consumer
    test_init_version_byteorder
    test_packet_boundaries
    test_resolve_errors
    test_udp_loopback
    test_tcp_loopback
    test_socket_set
)

foreach(test_program IN LISTS TEST_PROGRAMS)
    add_executable("${test_program}" "${test_program}.c")
    target_compile_features("${test_program}" PRIVATE c_std_99)
    target_link_libraries("${test_program}" PRIVATE
        "${SDL2_NET_TARGET}"
        "${SDL2_TARGET}"
    )
endforeach()

enable_testing()
foreach(test_program IN LISTS TEST_PROGRAMS)
    add_test(NAME "${test_program}" COMMAND "${test_program}")
endforeach()
