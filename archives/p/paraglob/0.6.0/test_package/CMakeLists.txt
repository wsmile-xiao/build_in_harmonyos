cmake_minimum_required(VERSION 3.15)
project(test_paraglob CXX)

# 消费者视角：通过 Conan 生成的 CMakeDeps 找到并链接已安装的 paraglob
find_package(paraglob REQUIRED)

add_executable(test_paraglob test_paraglob.cpp)
target_link_libraries(test_paraglob paraglob::paraglob)
set_target_properties(test_paraglob PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON)
