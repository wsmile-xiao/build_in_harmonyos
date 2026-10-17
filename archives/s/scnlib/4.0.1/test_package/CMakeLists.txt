cmake_minimum_required(VERSION 3.15)
project(test_scnlib CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(scn CONFIG REQUIRED)

add_executable(test_scnlib test.cpp)
target_link_libraries(test_scnlib PRIVATE scn::scn)
