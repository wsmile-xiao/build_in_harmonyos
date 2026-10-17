cmake_minimum_required(VERSION 3.16)
project(test_kimageannotator LANGUAGES CXX)

# Downstream contract simulation (kImageAnnotator 0.7.2 CMakeLists.txt
# L113/L115/L134/L140 verified line-by-line): consumers call
#   find_package(kImageAnnotator-Qt6 0.7.2 REQUIRED)
#   target_link_libraries(... kImageAnnotator::kImageAnnotator)
# The exported config runs find_dependency(Qt6 COMPONENTS Widgets) and the
# exported targets reference Qt6::Svg (PUBLIC link), so both Qt components
# must be found explicitly first.
find_package(Qt6 6.11.1 REQUIRED COMPONENTS Widgets Svg)
find_package(kImageAnnotator-Qt6 0.7.2 REQUIRED)
# The OHOS adaptation-point probe includes <X11/Xlib.h> directly; X11 is a
# PRIVATE dependency of the library and therefore not re-exported.
find_package(X11 REQUIRED)

add_executable(test_kimageannotator test_kimageannotator.cpp)
target_compile_features(test_kimageannotator PRIVATE cxx_std_17)
target_link_libraries(
    test_kimageannotator
    PRIVATE kImageAnnotator::kImageAnnotator Qt6::Widgets Qt6::Svg X11::X11
)
