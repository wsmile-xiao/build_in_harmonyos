cmake_minimum_required(VERSION 3.5)
cmake_policy(VERSION 3.5...3.13)

project(test_fastdds CXX)

find_package(fastdds REQUIRED)

add_executable(test_fastdds test_fastdds.cpp)
target_link_libraries(test_fastdds fastdds::fastrtps)

enable_testing()
add_test(NAME test_fastdds COMMAND test_fastdds)
