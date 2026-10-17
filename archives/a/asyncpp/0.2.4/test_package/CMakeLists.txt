cmake_minimum_required(VERSION 3.15)
project(test_asyncpp CXX)

# asyncpp 的 CMakeDeps 命名：cmake_file_name=asyncpp / cmake_target_name=asyncpp::asyncpp
find_package(asyncpp REQUIRED)

add_executable(test_asyncpp test_asyncpp.cpp)
target_link_libraries(test_asyncpp PRIVATE asyncpp::asyncpp)
set_target_properties(test_asyncpp PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
)
