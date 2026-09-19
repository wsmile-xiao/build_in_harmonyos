cmake_minimum_required(VERSION 3.15)
project(test_portaudiocxx LANGUAGES CXX)

find_package(portaudiocpp CONFIG REQUIRED)

add_executable(test_portaudiocxx test_portaudiocxx.cxx)
target_link_libraries(test_portaudiocxx PRIVATE portaudiocpp::portaudiocpp)
