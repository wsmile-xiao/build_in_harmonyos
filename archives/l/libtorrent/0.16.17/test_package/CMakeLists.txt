cmake_minimum_required(VERSION 3.15)
project(test_libtorrent LANGUAGES CXX)

find_package(libtorrent REQUIRED CONFIG)

add_executable(test_libtorrent test_libtorrent.cpp)
target_compile_features(test_libtorrent PRIVATE cxx_std_20)
target_link_libraries(test_libtorrent PRIVATE libtorrent::torrent)

enable_testing()
add_test(NAME test_libtorrent COMMAND test_libtorrent)
