cmake_minimum_required(VERSION 3.15)
project(liblzf_test_package C)

find_package(liblzf CONFIG REQUIRED)

add_executable(test_lzf test_lzf.c)
target_link_libraries(test_lzf PRIVATE liblzf::liblzf)

enable_testing()

# 5 consumer API cases, one ctest test each: ctest counts them, so
# discovered/executed/passed/failed come from the ctest log itself.
add_test(NAME api:roundtrip_text COMMAND test_lzf roundtrip_text)
add_test(NAME api:roundtrip_binary COMMAND test_lzf roundtrip_binary)
add_test(NAME api:roundtrip_large COMMAND test_lzf roundtrip_large)
add_test(NAME api:corrupt_einval COMMAND test_lzf corrupt_einval)
add_test(NAME api:small_out_e2big COMMAND test_lzf small_out_e2big)

# CLI case runs the packaged bin/lzf through POSIX sh. TEST_SH (a usable
# /bin/sh, resolved by test_package/conanfile.py) and LZF_BIN (absolute
# path of the packaged binary) are passed in with -D.
if(NOT DEFINED TEST_SH OR NOT DEFINED LZF_BIN)
    message(FATAL_ERROR "TEST_SH and LZF_BIN must be passed with -D (see test_package/conanfile.py)")
endif()
add_test(NAME cli:help_and_roundtrip
         COMMAND ${TEST_SH} ${CMAKE_CURRENT_SOURCE_DIR}/test_cli.sh)
set_tests_properties(cli:help_and_roundtrip PROPERTIES
                     ENVIRONMENT "LZF_BIN=${LZF_BIN}")
