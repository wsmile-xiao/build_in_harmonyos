cmake_minimum_required(VERSION 3.16)
project(test_libopenrazer LANGUAGES CXX)

# Qt6（qtbase cmake_find_mode=none，显式指向其 Qt6Config.cmake）
find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core DBus Gui Xml)

# libopenrazer：路径由 test_package/conanfile.py generate() 显式注入
# （qtbase cmake_find_mode=none，不用 CMakeDeps 解析本包）
add_executable(test_libopenrazer test_libopenrazer.cpp)
target_compile_features(test_libopenrazer PRIVATE cxx_std_17)
target_include_directories(test_libopenrazer PRIVATE ${LIBOPENRAZER_INCLUDE_DIR})
target_link_directories(test_libopenrazer PRIVATE ${LIBOPENRAZER_LIBRARY_DIR})
target_link_libraries(
    test_libopenrazer
    PRIVATE
        openrazer
        Qt6::Core
        Qt6::DBus
        Qt6::Gui
        Qt6::Xml
)
