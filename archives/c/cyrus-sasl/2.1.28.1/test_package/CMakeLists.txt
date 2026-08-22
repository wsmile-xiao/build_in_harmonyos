cmake_minimum_required(VERSION 3.16)
project(test_cyrus_sasl C)

find_package(cyrus-sasl REQUIRED CONFIG)

add_executable(test_cyrus_sasl test_cyrus_sasl.c)
target_link_libraries(test_cyrus_sasl PRIVATE cyrus-sasl::cyrus-sasl)

enable_testing()
add_test(NAME test_cyrus_sasl COMMAND test_cyrus_sasl)
