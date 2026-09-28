cmake_minimum_required(VERSION 3.15)
project(test_ctrack CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ctrack REQUIRED)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# R02 (P1/P2 修复): test_package 门禁必须实际构建并运行真实调用
# ctrack 公开 API 的使用者用例，而非只打印的空壳。全部三个用例都
# 通过公开头文件 ctrack.hpp + ctrack::ctrack 目标使用被测库。
add_executable(test_ctrack test_package.cpp)
target_link_libraries(test_ctrack ctrack::ctrack)

add_executable(consumer_app consumer_app.cpp)
target_link_libraries(consumer_app ctrack::ctrack)

add_executable(ohos_special_test ohos_special_test.cpp)
target_link_libraries(ohos_special_test ctrack::ctrack)

enable_testing()
add_test(NAME test_ctrack COMMAND test_ctrack)
add_test(NAME consumer_app COMMAND consumer_app)
add_test(NAME ohos_special_test COMMAND ohos_special_test)