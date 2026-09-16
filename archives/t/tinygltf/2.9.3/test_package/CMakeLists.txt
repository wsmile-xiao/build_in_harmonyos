cmake_minimum_required(VERSION 3.15)
project(test_tinygltf CXX)

find_package(tinygltf CONFIG REQUIRED)

add_executable(test_tinygltf test_tinygltf.cpp)
target_link_libraries(test_tinygltf PRIVATE tinygltf::tinygltf)
set_property(TARGET test_tinygltf PROPERTY CXX_STANDARD 11)
