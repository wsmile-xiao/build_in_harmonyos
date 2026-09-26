cmake_minimum_required(VERSION 3.20)
project(test_ctd_cli CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(ctd_cli REQUIRED)

add_executable(test_ctd_cli test.cpp)
target_link_libraries(test_ctd_cli PRIVATE ctd_cli::ctd_cli)

add_executable(test_ohos_specific ohos_specific_test.cpp)
target_link_libraries(test_ohos_specific PRIVATE ctd_cli::ctd_cli)

enable_testing()
add_test(NAME test_ctd_cli COMMAND test_ctd_cli)
add_test(NAME test_ohos_specific COMMAND test_ohos_specific)
