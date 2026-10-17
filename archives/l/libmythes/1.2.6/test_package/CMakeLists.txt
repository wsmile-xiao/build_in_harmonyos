cmake_minimum_required(VERSION 3.15)
project(test_mythes CXX)

find_package(libmythes REQUIRED)

add_executable(test_mythes test_mythes.cpp)
target_link_libraries(test_mythes libmythes::libmythes)

# Minimal thesaurus fixtures used by the consumer test (CWD = build dir).
file(COPY test_thes.idx test_thes.dat DESTINATION ${CMAKE_CURRENT_BINARY_DIR})

enable_testing()
add_test(NAME test_mythes COMMAND test_mythes)
