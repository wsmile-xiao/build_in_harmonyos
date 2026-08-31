cmake_minimum_required(VERSION 3.15)
project(test_libngf_qt CXX)
find_package(Qt5 CONFIG REQUIRED)
find_package(NGF-Qt CONFIG REQUIRED)
add_executable(test_libngf_qt test.cpp)
target_link_libraries(test_libngf_qt PRIVATE NGF::Qt Qt5::Core)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_libngf_qt PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_libngf_qt PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()
enable_testing()
add_test(NAME test_libngf_qt COMMAND $<TARGET_FILE:test_libngf_qt>)
