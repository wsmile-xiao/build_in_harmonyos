cmake_minimum_required(VERSION 3.15)
project(test_libvgm LANGUAGES C CXX)

find_package(libvgm REQUIRED)

add_executable(test_libvgm test.cpp)
target_link_libraries(test_libvgm PRIVATE libvgm::libvgm)
set_property(TARGET test_libvgm PROPERTY CXX_STANDARD 14)
set_property(TARGET test_libvgm PROPERTY CXX_STANDARD_REQUIRED ON)

# 消费者用例：下游"VGM→WAV 音乐转换器"场景（gzip 输入 + 整段渲染 + WAV 落盘回读校验）
add_executable(consumer_vgm_to_wav consumer_vgm_to_wav.cpp)
target_link_libraries(consumer_vgm_to_wav PRIVATE libvgm::libvgm)
set_property(TARGET consumer_vgm_to_wav PROPERTY CXX_STANDARD 14)
set_property(TARGET consumer_vgm_to_wav PROPERTY CXX_STANDARD_REQUIRED ON)
