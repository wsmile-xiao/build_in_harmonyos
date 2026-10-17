cmake_minimum_required(VERSION 3.15)
project(test_qt5_qtscxml CXX)

# qt5-qtbase exposes its modules through the aggregate Qt5Config.cmake
# (Qt5::Core targets). qt5-qtscxml adds the Qt5::Scxml target via its own
# cmake config (cmake_file_name=Qt5Scxml).
find_package(Qt5 CONFIG REQUIRED)
find_package(Qt5Scxml CONFIG REQUIRED)

add_executable(test_qt5_qtscxml test.cpp)
target_link_libraries(test_qt5_qtscxml PRIVATE Qt5::Scxml Qt5::Core)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_qt5_qtscxml PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_qt5_qtscxml PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()
enable_testing()
add_test(NAME test_qt5_qtscxml COMMAND $<TARGET_FILE:test_qt5_qtscxml>)
