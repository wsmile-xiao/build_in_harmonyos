cmake_minimum_required(VERSION 3.16)
project(test_ceres CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(test_ceres test_ceres.cpp)

# 优先走 Conan 生成的 CMake 配置：CeresConfig.cmake 由 CMakeDeps 产出，
# 并且因为 recipe 里声明了 cpp_info.requires = ["eigen::eigen"]，
# 它会自动 find_dependency(Eigen3) 并把 Eigen 的头文件目录一起带上。
# 这同时验证了「包的 CMake 交付面」是否可用。
find_package(Ceres CONFIG QUIET)
if(Ceres_FOUND)
  message(STATUS "test_ceres: 使用 find_package(Ceres) 的 imported target Ceres::ceres")
  target_link_libraries(test_ceres PRIVATE Ceres::ceres)
else()
  message(STATUS "test_ceres: 未找到 Ceres 配置包，回退为归档绝对路径链接")
  if(NOT CERES_PACKAGE_FOLDER)
    message(FATAL_ERROR "既没有 Ceres 配置包，也没有 CERES_PACKAGE_FOLDER")
  endif()
  target_include_directories(test_ceres PRIVATE
    "${CERES_PACKAGE_FOLDER}/include" ${DEP_INCLUDE_DIRS})
  set(_ceres_lib "${CERES_PACKAGE_FOLDER}/lib/libceres.a")
  if(NOT EXISTS "${_ceres_lib}")
    set(_ceres_lib "${CERES_PACKAGE_FOLDER}/lib/libceres.so")
  endif()
  target_link_libraries(test_ceres PRIVATE "${_ceres_lib}" m pthread)
endif()

enable_testing()
add_test(NAME test_ceres COMMAND test_ceres)
