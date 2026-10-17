cmake_minimum_required(VERSION 3.15)
project(test_fyba CXX)

# Find the package via Conan-generated CMakeDeps
find_package(fyba REQUIRED)

add_executable(test_fyba test.cpp)
target_link_libraries(test_fyba fyba::fyba)

add_executable(test_fyba_ohos test_ohos.cpp)
target_link_libraries(test_fyba_ohos fyba::fyba)

enable_testing()
add_test(NAME test_fyba COMMAND test_fyba)
add_test(NAME test_fyba_ohos COMMAND test_fyba_ohos)
