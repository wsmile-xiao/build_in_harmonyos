cmake_minimum_required(VERSION 3.15)
project(test_gason CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(gason REQUIRED)

add_executable(test_gason test_gason.cpp)
target_link_libraries(test_gason gason::gason)

add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos gason::gason)

enable_testing()
add_test(NAME test_gason COMMAND test_gason)
add_test(NAME test_ohos COMMAND test_ohos)