cmake_minimum_required(VERSION 3.15)
project(test_qtserialport CXX)

# CMakeDeps 生成（直接依赖场景，见 conan create 日志）：
#   find_package(Qt5)                        → qt5-qtbase 聚合 config (Qt5::Core 等)
#   find_package(qtserialport-opensource-src) → 被测包 config (Qt5::SerialPort)
find_package(Qt5 CONFIG REQUIRED)
find_package(qtserialport-opensource-src CONFIG REQUIRED)

add_executable(test_qtserialport test_qtserialport.cpp)
target_link_libraries(test_qtserialport PRIVATE Qt5::SerialPort Qt5::Core)

if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_qtserialport PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_qtserialport PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()

enable_testing()
add_test(NAME test_qtserialport COMMAND $<TARGET_FILE:test_qtserialport>)
