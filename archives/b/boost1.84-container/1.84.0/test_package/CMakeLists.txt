cmake_minimum_required(VERSION 3.15)
project(test_boost_container CXX)

find_package(Boost REQUIRED CONFIG COMPONENTS container)

add_executable(test_container test_container.cpp)
target_link_libraries(test_container PRIVATE Boost::container)

enable_testing()
add_test(NAME boost_container_test COMMAND test_container)
