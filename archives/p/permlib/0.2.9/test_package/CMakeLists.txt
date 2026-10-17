cmake_minimum_required(VERSION 3.15)
project(permlib_consumer_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# CMakeDeps 生成的 permlib-config.cmake（包名来自 package_info 的 cmake_file_name）。
# boost 的 include 目录由 permlib 的 cpp_info.requires = ["boost::headers"] 传递到
# permlib::permlib 的 INTERFACE 上 —— 消费者这里故意不写任何 boost 路径。
find_package(permlib CONFIG REQUIRED)

add_executable(permlib_consumer_test test.cpp)
target_link_libraries(permlib_consumer_test PRIVATE permlib::permlib)

enable_testing()
add_test(NAME permlib_consumer_test COMMAND permlib_consumer_test)
