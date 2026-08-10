cmake_minimum_required(VERSION 3.15)
project(test_hepmc3 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(hepmc3 REQUIRED)

add_executable(test_hepmc3 test_hepmc3.cpp)
target_link_libraries(test_hepmc3 hepmc3::hepmc3)

enable_testing()
add_test(NAME test_hepmc3 COMMAND test_hepmc3)
