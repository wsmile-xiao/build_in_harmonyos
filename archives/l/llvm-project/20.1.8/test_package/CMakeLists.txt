cmake_minimum_required(VERSION 3.20)
project(llvm_project_devface_probe CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── ① LLVM 开发面：LLVMConfig.cmake（LLVMExports + 组件依赖图）────────────────
find_package(LLVM REQUIRED CONFIG)
message(STATUS "LLVM_PROBE_VERSION=${LLVM_PACKAGE_VERSION}")
message(STATUS "LLVM_PROBE_CMAKE_DIR=${LLVM_CMAKE_DIR}")
message(STATUS "LLVM_PROBE_LIBRARY_DIRS=${LLVM_LIBRARY_DIRS}")
message(STATUS "LLVM_PROBE_INCLUDE_DIRS=${LLVM_INCLUDE_DIRS}")

# ── ② Clang 开发面：ClangConfig.cmake + ClangTargets*.cmake ───────────────────
find_package(Clang REQUIRED CONFIG)
message(STATUS "CLANG_PROBE_INCLUDE_DIRS=${CLANG_INCLUDE_DIRS}")

# ── ③ 下游 ispc 1.28.2 的原始判据 ─────────────────────────────────────────────
# ispc/CMakeLists.txt:411 `set(CLANG_LIBRARY_LIST clangFrontend clangBasic clangEdit clangLex
# clangSupport clangASTMatchers)` + :818 `find_library(... NAMES lib<name>.a clang-cpp
# HINTS ${LLVM_LIBRARY_DIRS})`。逐项断言命中包内静态库，缺一即下游不可用。
set(CLANG_PROBE_LIBS "")
foreach(_lib clangFrontend clangBasic clangEdit clangLex clangSupport clangASTMatchers)
  find_library(CLANG_PROBE_${_lib}_PATH
               NAMES "lib${_lib}.a" ${_lib}
               HINTS ${LLVM_LIBRARY_DIRS})
  if(NOT CLANG_PROBE_${_lib}_PATH)
    message(FATAL_ERROR "clang component '${_lib}' not found in LLVM_LIBRARY_DIRS=${LLVM_LIBRARY_DIRS}")
  endif()
  message(STATUS "CLANG_PROBE_${_lib}=${CLANG_PROBE_${_lib}_PATH}")
  list(APPEND CLANG_PROBE_LIBS "${CLANG_PROBE_${_lib}_PATH}")
endforeach()

# ── ④ 真实链接（R34 反空壳）：raw find_library 路径 + Clang/LLVM 导入目标 ──────
# 静态库之间有环（clang <-> LLVM），与 ispc 一样用 --start-group/--end-group 包裹。
add_executable(clang_devface_probe clang_devface_probe.cpp)
target_include_directories(clang_devface_probe PRIVATE ${LLVM_INCLUDE_DIRS} ${CLANG_INCLUDE_DIRS})
target_link_libraries(clang_devface_probe PRIVATE
  "-Wl,--start-group"
  ${CLANG_PROBE_LIBS}
  clangFrontend
  clangASTMatchers
  clangEdit
  clangLex
  clangSupport
  clangBasic
  "-Wl,--end-group")
