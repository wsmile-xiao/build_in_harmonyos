cmake_minimum_required(VERSION 3.16)
project(test_attica LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Network)
find_package(KF6Attica 6.28.0 REQUIRED)

add_executable(test_attica test.cpp)
target_link_libraries(test_attica PRIVATE Qt6::Core Qt6::Network KF6::Attica)

enable_testing()
add_test(NAME test_attica COMMAND test_attica)
