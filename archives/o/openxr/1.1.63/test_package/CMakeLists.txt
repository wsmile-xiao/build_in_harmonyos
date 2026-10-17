cmake_minimum_required(VERSION 3.16)
project(test_openxr CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 用上游自己安装的 CMake 包配置，而不是 conan 生成的 CMakeDeps 包装：
# 这样同时验了 lib/cmake/openxr/OpenXRConfig.cmake 与 OpenXRTargets.cmake
# 是真的可用（包对外承诺的一部分）。
find_package(OpenXR REQUIRED)

# loader 内核符号的 dlopen/dlsym 目标：一个最小 XR 运行时。
add_library(stub_runtime MODULE stub_runtime.cxx)
if(TARGET OpenXR::headers)
  target_link_libraries(stub_runtime PRIVATE OpenXR::headers)
else()
  target_include_directories(stub_runtime PRIVATE ${OpenXR_INCLUDE_DIR})
endif()

add_executable(test_openxr test_openxr.cxx)
target_link_libraries(test_openxr PRIVATE OpenXR::openxr_loader)
