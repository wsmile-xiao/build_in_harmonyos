cmake_minimum_required(VERSION 3.15)
project(test_mmap_allocator CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(mmap_allocator CONFIG REQUIRED)

add_executable(test_mmap_allocator test.cpp)
target_link_libraries(test_mmap_allocator PRIVATE mmap_allocator::mmap_allocator)

if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")
  add_executable(test_mmap_allocator_ohos test_ohos.cpp)
  target_compile_definitions(test_mmap_allocator_ohos PRIVATE MMAP_ALLOCATOR_HARMONYOS=1)
  target_link_libraries(test_mmap_allocator_ohos PRIVATE mmap_allocator::mmap_allocator)
endif()
