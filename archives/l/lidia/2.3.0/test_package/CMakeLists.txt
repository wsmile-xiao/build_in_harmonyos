cmake_minimum_required(VERSION 3.15)
project(lidia_consumer_test CXX)

# LiDIA 头文件是 C++98 时代产物，与库本体保持一致用 gnu++98 编译，
# 避免 libc++ 在新标准下的语法差异（库内 register / auto_ptr 等）。
set(CMAKE_CXX_STANDARD 98)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_CXX_STANDARD_REQUIRED OFF)

find_package(lidia REQUIRED)

add_executable(test_lidia_consumer src/test_lidia_consumer.cpp)
target_link_libraries(test_lidia_consumer PRIVATE lidia::lidia)
