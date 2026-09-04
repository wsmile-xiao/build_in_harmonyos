cmake_minimum_required(VERSION 3.15)
project(test_replxx CXX)

# Find the package via Conan-generated CMakeDeps
find_package(replxx REQUIRED)

add_executable(test_replxx ohos_spec_test.cxx)
target_link_libraries(test_replxx replxx::replxx)

enable_testing()
add_test(NAME test_replxx COMMAND test_replxx)
