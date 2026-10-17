cmake_minimum_required(VERSION 3.15)
project(test_rtm CXX)

# Find the package via Conan-generated CMakeDeps
find_package(rtm REQUIRED)

add_executable(test_rtm test.cpp)
target_link_libraries(test_rtm rtm::rtm)

enable_testing()
add_test(NAME test_rtm COMMAND test_rtm)