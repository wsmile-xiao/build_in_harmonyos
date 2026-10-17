cmake_minimum_required(VERSION 3.15)
project(test_sfml CXX)

find_package(SFML REQUIRED COMPONENTS system network)

add_executable(test_sfml test_sfml.cpp)
target_link_libraries(test_sfml PRIVATE SFML::System SFML::Network)

set_property(TARGET test_sfml PROPERTY CXX_STANDARD 17)
set_property(TARGET test_sfml PROPERTY CXX_STANDARD_REQUIRED ON)
