cmake_minimum_required(VERSION 3.12)
project(test_ecpint_consumer CXX)

find_package(ecpint CONFIG REQUIRED)

add_executable(test_ecpint test_ecpint.cpp)
set_property(TARGET test_ecpint PROPERTY CXX_STANDARD 11)
target_link_libraries(test_ecpint ECPINT::ecpint)
