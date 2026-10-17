cmake_minimum_required(VERSION 3.15)
project(test_libsoci CXX)

# Conan 生成的 SOCIConfig.cmake（recipe 声明 cmake_file_name=SOCI / cmake_target_name=SOCI::SOCI）
find_package(SOCI CONFIG REQUIRED)
# conan 生成的 sqlite3 配置：保证 soci/sqlite3/soci-sqlite3.h 里的 <sqlite3.h> 可见
find_package(sqlite3 CONFIG QUIET)

add_executable(test_libsoci test_libsoci.cpp)
set_target_properties(test_libsoci PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)

if(TARGET sqlite3::sqlite3)
  target_link_libraries(test_libsoci PRIVATE sqlite3::sqlite3)
endif()

# 两种 SOCI CMake 配置都能用：Conan 生成的是 SOCI::SOCI；上游自带的是 SOCI::soci_core 等分目标
if(TARGET SOCI::SOCI)
  target_link_libraries(test_libsoci PRIVATE SOCI::SOCI)
elseif(TARGET SOCI::soci_core)
  target_link_libraries(test_libsoci PRIVATE SOCI::soci_core SOCI::soci_sqlite3 SOCI::soci_empty)
else()
  message(FATAL_ERROR "找不到 SOCI 的 CMake 目标")
endif()
