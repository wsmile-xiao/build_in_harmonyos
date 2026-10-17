cmake_minimum_required(VERSION 3.15)
project(test_libkysdk-genai CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps (cmake_file_name = KysdkGenAiNlp)
find_package(KysdkGenAiNlp REQUIRED)

add_executable(test_libkysdk-genai test.cpp)
target_link_libraries(test_libkysdk-genai KysdkGenAiNlp::KysdkGenAiNlp)

enable_testing()
add_test(NAME test_libkysdk-genai COMMAND test_libkysdk-genai)
