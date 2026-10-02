cmake_minimum_required(VERSION 3.15)
project(test_gtl CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Consumer view: only the packaged include dir / imported target.
find_package(gtl REQUIRED)

add_executable(test_gtl test_package.cpp)
target_link_libraries(test_gtl gtl::gtl)
