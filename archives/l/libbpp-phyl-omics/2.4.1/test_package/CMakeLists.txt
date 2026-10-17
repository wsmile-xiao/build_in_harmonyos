cmake_minimum_required(VERSION 3.15)
project(test_libbpp_phyl_omics CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 直接链依赖包的静态归档（同族成熟做法）：OHOS/musl 加载器解析不了安装出的
# libbpp-phyl-omics.so 的斜杠相对 DT_NEEDED，链静态后消费者零运行期 .so 依赖。
# 归档来自被测包及其 Conan 依赖包的绝对目录（由 test_package/conanfile.py generate()
# 注入）。vendored libbpp-phyl.a 已并入 libbpp-phyl-omics 包，故从该包目录取。
set(_archives "")
foreach(_pair
    "LIBBPP_PHYL_OMICS_PACKAGE_FOLDER;libbpp-phyl-omics.a"
    "LIBBPP_PHYL_OMICS_PACKAGE_FOLDER;libbpp-phyl.a"
    "LIBBPP_SEQ_OMICS_PACKAGE_FOLDER;libbpp-seq-omics.a"
    "LIBBPP_SEQ_PACKAGE_FOLDER;libbpp-seq.a"
    "LIBBPP_SEQ_PACKAGE_FOLDER;libbpp-core.a")
  string(REPLACE ";" ";" _parts "${_pair}")
  list(GET _parts 0 _var)
  list(GET _parts 1 _lib)
  if(DEFINED ${_var})
    set(_path "${${_var}}/lib/${_lib}")
    if(EXISTS "${_path}")
      list(APPEND _archives "${_path}")
      include_directories("${${_var}}/include")
    endif()
  endif()
endforeach()

add_executable(test_bpp_phyl_omics test_bpp_phyl_omics.cpp)
if(_archives)
  target_link_libraries(test_bpp_phyl_omics PRIVATE ${_archives} m)
else()
  find_package(libbpp-phyl-omics CONFIG REQUIRED)
  target_link_libraries(test_bpp_phyl_omics PRIVATE libbpp-phyl-omics::libbpp-phyl-omics)
endif()

enable_testing()
add_test(NAME test_bpp_phyl_omics COMMAND test_bpp_phyl_omics)
