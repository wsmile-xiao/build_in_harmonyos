cmake_minimum_required(VERSION 3.15)
project(test_qt3d_opensource_src CXX)
# CMakeDeps generates one config per package (package-level cmake_file_name):
# "Qt5" (qt5-qtbase) and "Qt53D" (this package); component targets such as
# Qt5::3DCore are declared by the package config, not by per-component configs.
find_package(Qt5 CONFIG REQUIRED)
find_package(Qt53D CONFIG REQUIRED)
add_executable(test_qt3d_opensource_src test.cpp)
target_link_libraries(test_qt3d_opensource_src PRIVATE Qt5::3DCore Qt5::Core)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_qt3d_opensource_src PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_qt3d_opensource_src PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()
enable_testing()
add_test(NAME test_qt3d_opensource_src COMMAND $<TARGET_FILE:test_qt3d_opensource_src>)
