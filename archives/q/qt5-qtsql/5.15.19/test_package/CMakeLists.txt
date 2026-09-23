cmake_minimum_required(VERSION 3.5)
project(test_qtsql CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 消费路径：conan CMakeDeps 形态（qt5 主包/qt5-qtsql 均为 conan 生成
# config，仓内 Qt5 生态统一形态——qt5 主包无原生 Qt5CoreConfig.cmake，
# 原生 find_package(Qt5 COMPONENTS Sql) 路径需主包补 config 后开启，
# 本包已打包 lib/cmake/Qt5Sql/Qt5SqlConfig.cmake 备原生消费就绪）。
find_package(qt5-qtsql REQUIRED)
find_package(qt5 REQUIRED)

add_executable(test_qtsql test_qtsql.cpp)
target_link_libraries(test_qtsql PRIVATE qt5-qtsql::qt5-qtsql qt5::qt5)
