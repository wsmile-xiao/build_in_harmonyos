cmake_minimum_required(VERSION 3.16)
project(test_tinydng CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(tinydng CONFIG REQUIRED)

add_executable(test_tinydng test_tinydng.cpp)
target_link_libraries(test_tinydng PRIVATE tinydng::tinydng)

enable_testing()
add_test(NAME test_tinydng COMMAND test_tinydng)
