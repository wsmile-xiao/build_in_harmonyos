cmake_minimum_required(VERSION 3.15)
project(cubelib_consumer CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(cubelib CONFIG REQUIRED)

add_executable(cubelib_api_contract test_cube_api.cpp)
target_compile_options(cubelib_api_contract PRIVATE -Wall -Wextra)
target_link_libraries(cubelib_api_contract PRIVATE cubelib::cubelib)

add_executable(cubelib_write_contract test_cube_write.cpp)
target_compile_options(cubelib_write_contract PRIVATE -Wall -Wextra)
target_link_libraries(cubelib_write_contract PRIVATE cubelib::cubelib)

enable_testing()
add_test(NAME cubelib_api_contract COMMAND cubelib_api_contract)
add_test(NAME cubelib_write_contract COMMAND cubelib_write_contract)
