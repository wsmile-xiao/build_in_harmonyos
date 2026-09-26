cmake_minimum_required(VERSION 3.15)
project(test_boolinq CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Consumer view: only the packaged include dir / imported target.
find_package(boolinq REQUIRED)

add_executable(test_boolinq test_package.cpp)
target_link_libraries(test_boolinq boolinq::boolinq)
