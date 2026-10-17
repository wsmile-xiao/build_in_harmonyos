cmake_minimum_required(VERSION 3.16)
project(test_kcompactdisc CXX)

find_package(KCompactDisc6 REQUIRED CONFIG)

add_executable(test_kcompactdisc test_kcompactdisc.cpp)
target_link_libraries(test_kcompactdisc KCompactDisc6)

enable_testing()
add_test(NAME test_kcompactdisc COMMAND test_kcompactdisc)
