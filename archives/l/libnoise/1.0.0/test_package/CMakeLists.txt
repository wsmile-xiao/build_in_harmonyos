cmake_minimum_required(VERSION 3.15)
project(test_libnoise LANGUAGES CXX)

find_package(libnoise REQUIRED)

add_executable(test_libnoise test_libnoise.cpp)
target_link_libraries(test_libnoise libnoise::libnoise)

enable_testing()
add_test(NAME test_libnoise COMMAND test_libnoise)
