cmake_minimum_required(VERSION 3.15)
project(test_backport_cpp CXX)

# backport-cpp 是 header-only：CMakeDeps 按包的 cmake_file_name=Backport /
# cmake_target_name=Backport::Backport 生成配置
find_package(Backport REQUIRED)

add_executable(test_backport_cpp test_backport_cpp.cpp)
target_link_libraries(test_backport_cpp PRIVATE Backport::Backport)
set_target_properties(test_backport_cpp PROPERTIES
  CXX_STANDARD 11
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
)
