cmake_minimum_required(VERSION 3.15)
project(test_fftwpp CXX)

find_package(fftwpp REQUIRED)
find_package(fftw REQUIRED)

# fftwpp 伴随编译单元（上游示例用法：g++ example0.cc ../fftw++.cc -lfftw3）。
# fftwpp 包把 fftw++.cc/parallel.cc 放在 srcdir（cpp_info.srcdirs → <pkg>/src/fftwpp），
# 由 test_package/conanfile.py 从依赖的 package_folder 定位后经
# -DFFTWPP_SRC_DIR=... 传入（比解析 CMakeDeps 变量/生成器表达式更稳）。
if(NOT DEFINED FFTWPP_SRC_DIR)
  message(FATAL_ERROR "FFTWPP_SRC_DIR not provided (expected conanfile.py -D)")
endif()
if(NOT EXISTS "${FFTWPP_SRC_DIR}/fftw++.cc")
  message(FATAL_ERROR "fftwpp companion sources not found in ${FFTWPP_SRC_DIR}")
endif()

# 伴随 .cc 里的 #include "fftw++.h"/"parallel.h" 是引号包含：默认相对 .cc 自身
# 目录查找，而包内头文件在 <pkg>/include/fftwpp/ 下——把该目录显式加进搜索路径。
get_filename_component(FFTWPP_PKG_ROOT "${FFTWPP_SRC_DIR}" DIRECTORY)
get_filename_component(FFTWPP_PKG_ROOT "${FFTWPP_PKG_ROOT}" DIRECTORY)
add_executable(test_fftwpp
  test.cpp
  "${FFTWPP_SRC_DIR}/fftw++.cc"
  "${FFTWPP_SRC_DIR}/parallel.cc")
target_link_libraries(test_fftwpp PRIVATE fftwpp::fftwpp fftw::fftw)
# 让伴随 .cc 的引号 include 解析到包内 include/fftwpp/（test.cpp 用
# <fftwpp/fftw++.h> 尖括号包含，两不冲突）
target_include_directories(test_fftwpp PRIVATE "${FFTWPP_PKG_ROOT}/include/fftwpp")

set_property(TARGET test_fftwpp PROPERTY CXX_STANDARD 11)
set_property(TARGET test_fftwpp PROPERTY CXX_STANDARD_REQUIRED ON)
