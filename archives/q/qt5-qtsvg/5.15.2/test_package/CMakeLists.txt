cmake_minimum_required(VERSION 3.15)
project(test_qt5_qtsvg CXX)
find_package(qt5-qtsvg CONFIG REQUIRED)
find_package(qt5-qtbase CONFIG REQUIRED)
add_executable(test_qt5_qtsvg test.cpp)
target_link_libraries(test_qt5_qtsvg PRIVATE Qt5::Svg Qt5::Core Qt5::Gui)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_qt5_qtsvg PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_qt5_qtsvg PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()
enable_testing()
add_test(NAME test_qt5_qtsvg COMMAND $<TARGET_FILE:test_qt5_qtsvg>)
