cmake_minimum_required(VERSION 3.15)
project(test_zfp C)

find_package(zfp CONFIG REQUIRED)

add_executable(test_zfp test.c)
target_link_libraries(test_zfp PRIVATE zfp::zfp)

enable_testing()
add_test(NAME zfp_roundtrip COMMAND test_zfp)
