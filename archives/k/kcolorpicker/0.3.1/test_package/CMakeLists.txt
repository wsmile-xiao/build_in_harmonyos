cmake_minimum_required(VERSION 3.16)
project(test_kcolorpicker LANGUAGES CXX)

# 下游契约模拟（kImageAnnotator-0.7.2 CMakeLists.txt L46/L47/L79 逐行核验）：
#   find_package(kColorPicker-Qt${QT_MAJOR_VERSION} 0.3.1 REQUIRED)
#   target_link_libraries(... PRIVATE kColorPicker::kColorPicker)
# Qt6::Widgets 需先显式找到，导出 target 的 INTERFACE_LINK_LIBRARIES
# 引用 Qt6::Widgets（上游 PUBLIC 链接）。
find_package(Qt6 6.11.1 REQUIRED COMPONENTS Widgets)
find_package(kColorPicker-Qt6 0.3.1 REQUIRED)

add_executable(test_kcolorpicker test_kcolorpicker.cpp)
target_compile_features(test_kcolorpicker PRIVATE cxx_std_17)
target_link_libraries(
    test_kcolorpicker
    PRIVATE kColorPicker::kColorPicker Qt6::Widgets
)
