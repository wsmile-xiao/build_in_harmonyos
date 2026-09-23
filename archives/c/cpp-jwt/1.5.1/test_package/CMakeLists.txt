cmake_minimum_required(VERSION 3.15)
project(test_cpp-jwt CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(cpp-jwt REQUIRED)

add_executable(test_cpp-jwt test_package.cpp)
target_link_libraries(test_cpp-jwt PRIVATE cpp-jwt::cpp-jwt)

add_executable(ohos_adapt_test ohos_adapt_test.cpp)
target_link_libraries(ohos_adapt_test PRIVATE cpp-jwt::cpp-jwt)

enable_testing()
add_test(NAME test_cpp-jwt COMMAND test_cpp-jwt)
add_test(NAME ohos_adapt_test COMMAND ohos_adapt_test)
