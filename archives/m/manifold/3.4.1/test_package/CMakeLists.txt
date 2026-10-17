cmake_minimum_required(VERSION 3.15)
project(test_manifold CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(manifold CONFIG REQUIRED)

add_executable(test_manifold test_manifold.cpp)
# manifold was built with MANIFOLD_CROSS_SECTION=ON; mirror that so the 2D
# CrossSection API (in manifold/cross_section.h, pulled conditionally by
# manifold.h) is exposed to the consumer translation unit.
target_compile_definitions(test_manifold PRIVATE MANIFOLD_CROSS_SECTION=1)
target_link_libraries(test_manifold PRIVATE manifold::manifold)
