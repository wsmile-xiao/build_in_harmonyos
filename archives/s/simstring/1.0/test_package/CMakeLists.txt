cmake_minimum_required(VERSION 3.15)
project(test_simstring CXX)

# Consumer of the packaged header-only library (simstring::simstring target).
find_package(simstring REQUIRED)

add_executable(test_simstring test.cpp)
target_link_libraries(test_simstring PRIVATE simstring::simstring m)
