cmake_minimum_required(VERSION 3.15)
project(test_kfilemetadata CXX)

find_package(KF6FileMetaData REQUIRED)

add_executable(test_kfilemetadata test.cpp)
target_link_libraries(test_kfilemetadata KF6::FileMetaData)

enable_testing()
add_test(NAME test_kfilemetadata COMMAND test_kfilemetadata)
