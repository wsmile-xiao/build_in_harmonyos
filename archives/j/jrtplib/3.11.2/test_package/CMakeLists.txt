cmake_minimum_required(VERSION 3.15)
project(test_jrtplib LANGUAGES CXX)

find_package(jrtplib CONFIG REQUIRED)

add_executable(test_version test_version.cpp)
target_compile_features(test_version PRIVATE cxx_std_11)
target_link_libraries(test_version PRIVATE jrtplib::jrtplib)

add_executable(test_packet test_packet.cpp)
target_compile_features(test_packet PRIVATE cxx_std_11)
target_link_libraries(test_packet PRIVATE jrtplib::jrtplib)

enable_testing()
add_test(NAME version COMMAND test_version)
add_test(NAME packet COMMAND test_packet)
