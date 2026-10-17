cmake_minimum_required(VERSION 3.15)
project(test_bambamc C)

find_package(bambamc REQUIRED)

add_executable(test_bambamc test_bambamc.c)
target_link_libraries(test_bambamc bambamc::bambamc)

enable_testing()
add_test(NAME test_bambamc COMMAND test_bambamc consumer_roundtrip.bam)
