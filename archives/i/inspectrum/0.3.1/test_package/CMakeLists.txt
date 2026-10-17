cmake_minimum_required(VERSION 3.15)
project(test_inspectrum CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Qt5 配置来自 qt5-qtbase 包内真实 config（CMAKE_PREFIX_PATH 已指向包根）
find_package(Qt5 REQUIRED COMPONENTS Core Widgets Concurrent)

add_executable(test_inspectrum test.cpp)

target_include_directories(test_inspectrum PRIVATE
    ${FFTW_INC}
    ${LIQUID_INC})

target_link_libraries(test_inspectrum
    Qt5::Core Qt5::Widgets Qt5::Concurrent
    ${FFTW_LIB}
    ${LIQUID_LIB})
