cmake_minimum_required(VERSION 3.22)
project(juce_ohos_test VERSION 8.0.5 LANGUAGES C CXX)

# juce 包自带官方 JUCEConfig.cmake（lib/cmake/JUCE-8.0.5）；经工具链变量
# JUCE_PACKAGE_DIR 注入包前缀，find_package 解析原始 config。
list(APPEND CMAKE_PREFIX_PATH "${JUCE_PACKAGE_DIR}")

find_package(JUCE REQUIRED CONFIG)

juce_add_console_app(test_juce_app)

target_sources(test_juce_app PRIVATE test_juce.cpp)

target_compile_definitions(test_juce_app PRIVATE
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0)

# 消费方真实路径：INTERFACE 模块源编入本目标，pkg-config 依赖（freetype2/
# fontconfig 共享库按 E505 实体化签名+rpath、X11 头 NOLINK）由
# juce_add_module 的 linuxPackages 分支接线。
target_link_libraries(test_juce_app PRIVATE
    juce::juce_core
    juce::juce_events
    juce::juce_graphics
    juce::juce_recommended_config_flags)

enable_testing()
add_test(NAME test_juce_app COMMAND test_juce_app)
