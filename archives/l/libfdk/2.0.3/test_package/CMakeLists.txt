cmake_minimum_required(VERSION 3.15)
project(test_libfdk C)

find_package(fdk-aac CONFIG REQUIRED)

add_executable(test_libfdk test_libfdk.c)
target_link_libraries(test_libfdk PRIVATE FDK-AAC::fdk-aac)

enable_testing()
add_test(NAME encoder_open_close COMMAND test_libfdk encoder)
add_test(NAME decoder_open_close COMMAND test_libfdk decoder)
add_test(NAME roundtrip_mono COMMAND test_libfdk roundtrip-mono)
add_test(NAME roundtrip_stereo COMMAND test_libfdk roundtrip-stereo)
