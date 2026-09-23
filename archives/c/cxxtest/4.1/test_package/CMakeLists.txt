cmake_minimum_required(VERSION 3.15)
project(test_cxxtest CXX)

find_package(CxxTest REQUIRED)

# generated_runner.cpp is produced by the packaged cxxtestgen driver in the
# consumer test's generate() step (see conanfile.py); it #includes the suite
# header from the source directory and the cxxtest/ headers from the package.
add_executable(test_cxxtest "${CMAKE_BINARY_DIR}/generated_runner.cpp")
target_include_directories(test_cxxtest PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(test_cxxtest PRIVATE CxxTest::CxxTest)
