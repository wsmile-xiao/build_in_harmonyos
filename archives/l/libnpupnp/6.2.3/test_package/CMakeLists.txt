cmake_minimum_required(VERSION 3.15)
project(test_npupnp CXX)

find_package(libnpupnp CONFIG REQUIRED)

add_executable(test_npupnp test_npupnp.cpp)
target_link_libraries(test_npupnp PRIVATE libnpupnp::libnpupnp)

enable_testing()
add_test(NAME test_npupnp COMMAND test_npupnp)
