cmake_minimum_required(VERSION 3.15)
project(openmama_consumer LANGUAGES C CXX)

find_package(openmama REQUIRED)
find_package(apr REQUIRED)

add_executable(test_openmama_c test_openmama.c)
target_link_libraries(test_openmama_c PRIVATE openmama::openmama)

add_executable(test_openmama_cpp test_openmama_cpp.cpp)
target_link_libraries(test_openmama_cpp PRIVATE openmama::openmama)

add_executable(test_openmama_uri test_openmama_uri.c)
target_link_libraries(test_openmama_uri PRIVATE openmama::openmama apr::apr)
