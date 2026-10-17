cmake_minimum_required(VERSION 3.15)
project(boost_filesystem_consumer CXX)

find_package(boost1.84-filesystem CONFIG REQUIRED)
add_executable(boost_filesystem_test test_filesystem.cpp)
target_link_libraries(boost_filesystem_test PRIVATE boost1.84-filesystem::boost1.84-filesystem)
target_compile_features(boost_filesystem_test PRIVATE cxx_std_17)

enable_testing()
add_test(NAME boost_filesystem_test COMMAND boost_filesystem_test)
