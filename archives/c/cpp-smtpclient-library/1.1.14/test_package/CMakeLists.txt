cmake_minimum_required(VERSION 3.15)
project(test_cpp-smtpclient-library CXX)

# Find the package via Conan-generated CMakeDeps
find_package(smtpclient REQUIRED)

add_executable(test_cpp-smtpclient-library test.cpp)
target_link_libraries(test_cpp-smtpclient-library smtpclient::smtpclient)

enable_testing()
add_test(NAME test_cpp-smtpclient-library COMMAND test_cpp-smtpclient-library)
