cmake_minimum_required(VERSION 3.15)
project(test_qtbase_opensource_src CXX)
find_package(Qt5 CONFIG REQUIRED)
add_executable(test_qtbase_opensource_src test.cpp)
target_link_libraries(test_qtbase_opensource_src PRIVATE
    Qt5::Core Qt5::Gui Qt5::Network Qt5::Test
    Qt5::Widgets Qt5::Xml Qt5::PrintSupport)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_qtbase_opensource_src PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_qtbase_opensource_src PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()
enable_testing()
add_test(NAME test_qtbase_opensource_src COMMAND $<TARGET_FILE:test_qtbase_opensource_src>)
