cmake_minimum_required(VERSION 3.15)
project(test_syndication CXX)

find_package(KF6Syndication REQUIRED)
find_package(Qt6Core REQUIRED)

add_executable(test_syndication test.cpp)
target_link_libraries(test_syndication KF6::Syndication Qt6::Core)

enable_testing()
add_test(NAME test_syndication COMMAND test_syndication)
