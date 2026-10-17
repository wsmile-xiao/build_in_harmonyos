cmake_minimum_required(VERSION 3.15)
project(test_mdspan CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 只通过 Conan 生成的 CMakeDeps 配置找包（不碰上游源码树）
find_package(mdspan REQUIRED CONFIG)

if(NOT TARGET std::mdspan)
  message(FATAL_ERROR "std::mdspan target missing: cpp_info.cmake_target_name 未对齐上游 install(EXPORT NAMESPACE std::)")
endif()

# 指纹与文件数由 test_package/conanfile.py generate() 从**已安装的包**取值注入
if(NOT MDSPAN_INSTALLED_HDR_SHA256)
  set(MDSPAN_INSTALLED_HDR_SHA256 "")
endif()
if(NOT MDSPAN_INSTALLED_FILECOUNT)
  set(MDSPAN_INSTALLED_FILECOUNT 0)
endif()

add_executable(consumer consumer.cpp)
target_link_libraries(consumer PRIVATE std::mdspan)
target_compile_definitions(consumer PRIVATE
  MDSPAN_INSTALLED_HDR_SHA256="${MDSPAN_INSTALLED_HDR_SHA256}"
  MDSPAN_INSTALLED_FILECOUNT=${MDSPAN_INSTALLED_FILECOUNT})

add_executable(ohos_special_test ohos_special_test.cpp)
target_link_libraries(ohos_special_test PRIVATE std::mdspan)
