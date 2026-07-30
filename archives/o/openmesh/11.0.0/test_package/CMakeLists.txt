cmake_minimum_required(VERSION 3.15)
project(test_openmesh LANGUAGES CXX)

find_package(OpenMesh REQUIRED CONFIG)

add_executable(test_openmesh test_openmesh.cpp)
target_link_libraries(test_openmesh PRIVATE OpenMesh::OpenMesh)
target_compile_features(test_openmesh PRIVATE cxx_std_11)
