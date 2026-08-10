cmake_minimum_required(VERSION 3.15)
project(test_disomaster LANGUAGES C CXX)

find_package(disomaster CONFIG REQUIRED)

add_executable(test_disomaster test.cpp)
add_executable(fake_xorriso fake_xorriso.c)

target_compile_features(test_disomaster PRIVATE cxx_std_11)
target_link_libraries(test_disomaster PRIVATE disomaster::disomaster)

# 手动添加 Qt5 路径（CMakeDeps 组件级 includedirs/libdirs 在此环境未正确传递）
if(DEFINED QT5_INCLUDE_DIR)
    target_include_directories(test_disomaster PRIVATE ${QT5_INCLUDE_DIR})
endif()
if(DEFINED QT5_CORE_INCLUDE_DIR)
    target_include_directories(test_disomaster PRIVATE ${QT5_CORE_INCLUDE_DIR})
endif()
if(DEFINED QT5_LIB_DIR)
    find_library(QT5_CORE_LIB NAMES Qt5Core PATHS ${QT5_LIB_DIR} NO_DEFAULT_PATH)
    if(QT5_CORE_LIB)
        target_link_libraries(test_disomaster PRIVATE ${QT5_CORE_LIB})
    endif()
endif()

# OHOS 平台需要链接 C++ 运行时库
if(CMAKE_SYSTEM_NAME MATCHES "OHOS|HarmonyOS")
    target_link_options(test_disomaster PRIVATE -stdlib=libc++)
    if(DEFINED OHOS_CXX_RUNTIME_DIR)
        target_link_libraries(test_disomaster PRIVATE
            "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
            "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
            "${OHOS_CXX_RUNTIME_DIR}/libunwind.a")
    endif()
endif()
