cmake_minimum_required(VERSION 3.15)
project(test_kiconthemes CXX)

# Qt6Config.cmake defines the _qt_internal_* macros that Qt6SvgConfig.cmake
# relies on, so load it first, then find Qt6Svg as its own package.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(Qt6Svg REQUIRED)
find_package(KF6IconThemes REQUIRED)

add_executable(test_kiconthemes test.cpp)
target_link_libraries(test_kiconthemes KF6::IconThemes)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_link_options(test_kiconthemes PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
endif()

enable_testing()
add_test(NAME test_kiconthemes COMMAND test_kiconthemes)
