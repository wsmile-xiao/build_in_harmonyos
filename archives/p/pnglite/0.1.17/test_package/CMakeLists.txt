cmake_minimum_required(VERSION 3.15)
project(test_pnglite LANGUAGES C)

find_package(pnglite REQUIRED CONFIG)

add_executable(test_pnglite test_pnglite.c)
target_link_libraries(test_pnglite PRIVATE pnglite::pnglite)

add_executable(harmonyos_specific_test harmonyos_specific_test.c)
target_link_libraries(harmonyos_specific_test PRIVATE pnglite::pnglite)

enable_testing()
add_test(NAME pnglite_api_roundtrip COMMAND test_pnglite)
add_test(NAME pnglite_harmonyos_platform COMMAND harmonyos_specific_test)
