cmake_minimum_required(VERSION 3.15)
project(test_opencsg CXX)

# Package is located through the Conan-generated CMakeDeps config
# (openCSG exports cmake_file_name=OpenCSG, cmake_target_name=OpenCSG::opencsg).
find_package(OpenCSG REQUIRED)

add_executable(test_opencsg test_opencsg.cpp)
target_compile_features(test_opencsg PRIVATE cxx_std_17)
target_link_libraries(test_opencsg PRIVATE OpenCSG::opencsg)
