cmake_minimum_required(VERSION 3.16)
project(sheenbidi_consumer C)

enable_testing()

find_package(SheenBidi CONFIG REQUIRED)

add_executable(sheenbidi_consumer test_sheenbidi.c)
target_link_libraries(sheenbidi_consumer PRIVATE SheenBidi::SheenBidi)

add_test(NAME consumer_assertions COMMAND sheenbidi_consumer)
