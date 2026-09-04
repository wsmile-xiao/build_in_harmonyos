cmake_minimum_required(VERSION 3.15)
project(array_hash_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(tsl-array-hash CONFIG REQUIRED)

add_executable(array_hash_test test.cpp)
target_link_libraries(array_hash_test PRIVATE tsl::array_hash)

enable_testing()
add_test(NAME array_hash_test COMMAND array_hash_test)
