cmake_minimum_required(VERSION 3.15)
project(test_flac_consumer C)

find_package(FLAC REQUIRED CONFIG)

add_executable(test_flac_consumer test_flac_consumer.c)
target_link_libraries(test_flac_consumer PRIVATE FLAC::FLAC)

enable_testing()
add_test(NAME flac_consumer COMMAND test_flac_consumer)
