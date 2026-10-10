cmake_minimum_required(VERSION 3.15)
project(test_qtpositioning CXX)
find_package(Qt5 CONFIG REQUIRED)
find_package(Qt5Positioning CONFIG REQUIRED)
find_package(Qt5Qml CONFIG REQUIRED)
add_executable(test_qtpositioning test.cpp)
target_link_libraries(test_qtpositioning PRIVATE Qt5::Positioning Qt5::Core Qt5::Qml)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_qtpositioning PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_qtpositioning PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()
enable_testing()
add_test(NAME test_qtpositioning COMMAND $<TARGET_FILE:test_qtpositioning>)
