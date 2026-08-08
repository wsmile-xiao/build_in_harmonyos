cmake_minimum_required(VERSION 3.15)
project(test_sfml LANGUAGES CXX)

find_package(SFML CONFIG REQUIRED COMPONENTS system network)

add_executable(test_sfml test.cpp)
target_compile_features(test_sfml PRIVATE cxx_std_11)
target_link_libraries(test_sfml PRIVATE sfml-network sfml-system)
