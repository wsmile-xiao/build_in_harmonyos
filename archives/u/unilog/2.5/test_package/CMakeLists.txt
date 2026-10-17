cmake_minimum_required(VERSION 3.5)
project(test_unilog CXX)
# unilog is the only required package; glog headers are transitive via unilog::unilog
# (package_info propagates glog includes + cpp_info.requires ensures CMakeDeps link)
find_package(unilog REQUIRED CONFIG)

add_executable(test_unilog test.cpp)
target_link_libraries(test_unilog PRIVATE unilog::unilog)
target_compile_features(test_unilog PRIVATE cxx_std_17)
# Ensure the binary is placed in a known location for conanfile.py
set_target_properties(test_unilog PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
# Also declare ctest
enable_testing()
add_test(NAME test_unilog COMMAND test_unilog)
