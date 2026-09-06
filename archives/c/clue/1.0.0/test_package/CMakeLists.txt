cmake_minimum_required(VERSION 3.15)
project(test_clue_consumer CXX)

find_package(clue REQUIRED)

add_executable(test_clue_consumer test_clue_consumer.cpp)
target_link_libraries(test_clue_consumer PRIVATE clue::clue)
# clue advertises itself as a C++03 library: compile the consumer with the
# strictest advertised standard to prove the packaged header is usable there.
set_target_properties(test_clue_consumer PROPERTIES CXX_STANDARD 98 CXX_STANDARD_REQUIRED ON)
