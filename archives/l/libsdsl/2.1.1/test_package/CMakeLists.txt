cmake_minimum_required(VERSION 3.15)
project(test_sdsl CXX)

find_package(libsdsl REQUIRED)

add_executable(test_sdsl test_sdsl.cpp)
target_link_libraries(test_sdsl libsdsl::libsdsl)

enable_testing()
add_test(NAME test_sdsl COMMAND test_sdsl)
