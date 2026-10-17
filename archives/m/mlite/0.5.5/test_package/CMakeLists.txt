cmake_minimum_required(VERSION 3.15)
project(test_mlite CXX)

# Qt5：qt5-qtbase/5.15.2.2 以组件级 cmake_file_name 导出（Qt5Core / Qt5DBus …）
find_package(Qt5 CONFIG REQUIRED)
# mlite：本仓配方 package_info 设 cmake_file_name=MLite / cmake_target_name=MLite::MLite
find_package(MLite CONFIG REQUIRED)

add_executable(test_mlite test.cpp)
target_link_libraries(test_mlite PRIVATE MLite::MLite Qt5::Core Qt5::DBus ${CMAKE_DL_LIBS})

if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_mlite PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_mlite PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()

enable_testing()
add_test(NAME test_mlite COMMAND $<TARGET_FILE:test_mlite>)
