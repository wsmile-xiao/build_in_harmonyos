cmake_minimum_required(VERSION 3.15)
project(test_crow CXX)

find_package(Crow REQUIRED)

add_executable(test_crow test_crow.cpp)
target_link_libraries(test_crow PRIVATE Crow::Crow)
set_target_properties(test_crow PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
)
