cmake_minimum_required(VERSION 3.16)
project(test_qt5svg CXX)

# CMakeDeps 实际生成包级 config（create 日志确认）：
#   find_package(qt5-qtsvg) + qt5-qtsvg::qt5-qtsvg
# （组件级 Qt5SvgConfig 由包内自带，此处用包级目标最稳）
find_package(qt5-qtsvg CONFIG REQUIRED)
find_package(qt5-qtbase CONFIG REQUIRED)

add_executable(test_qt5svg test.cpp)
target_link_libraries(test_qt5svg PRIVATE qt5-qtsvg::qt5-qtsvg qt5-qtbase::qt5-qtbase)
