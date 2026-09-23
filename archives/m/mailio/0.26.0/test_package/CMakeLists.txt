cmake_minimum_required(VERSION 3.15)
project(test_mailio CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(mailio REQUIRED)
find_package(Boost REQUIRED)

add_executable(test_mailio test.cpp)
target_link_libraries(test_mailio mailio::mailio Boost::boost)
