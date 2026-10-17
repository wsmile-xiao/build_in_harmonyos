cmake_minimum_required(VERSION 3.15)
project(test_osg_consumer CXX)

set(CMAKE_CXX_STANDARD 17)

# Conan CMakeDeps (cmake_file_name=OpenSceneGraph) exposes the imported
# target OpenSceneGraph::OpenSceneGraph carrying include dirs + libs.
find_package(OpenSceneGraph REQUIRED)

add_executable(test_osg_consumer test_osg_consumer.cpp)
target_link_libraries(test_osg_consumer OpenSceneGraph::OpenSceneGraph)

enable_testing()
add_test(NAME test_osg_consumer COMMAND test_osg_consumer)
