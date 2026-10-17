cmake_minimum_required(VERSION 3.16)
project(test_attica LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Network)
find_package(KF5Attica 5.116.0 REQUIRED)

add_executable(test_attica test.cpp)
target_link_libraries(test_attica PRIVATE Qt5::Core Qt5::Network KF5::Attica)

enable_testing()
add_test(NAME test_attica COMMAND test_attica)
