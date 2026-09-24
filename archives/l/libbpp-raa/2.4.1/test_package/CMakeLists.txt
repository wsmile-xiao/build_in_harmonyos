cmake_minimum_required(VERSION 3.15)
project(test_libbpp_raa CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 按绝对路径链 4 个静态归档（bpp-raa → bpp-seq → bpp-core → z），
# 与 libbpp-phyl 的 test_package 同法，消费者零运行期 .so 依赖。
set(_archives "")
foreach(_pair
    "LIBBPP_RAA_PACKAGE_FOLDER;libbpp-raa.a"
    "LIBBPP_SEQ_PACKAGE_FOLDER;libbpp-seq.a"
    "LIBBPP_SEQ_PACKAGE_FOLDER;libbpp-core.a"
    "ZLIB_PACKAGE_FOLDER;libz.a")
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

add_executable(test_bpp_raa test_bpp_raa.cpp)
if(_archives)
  target_link_libraries(test_bpp_raa PRIVATE ${_archives} m)
else()
  find_package(libbpp-raa CONFIG REQUIRED)
  target_link_libraries(test_bpp_raa PRIVATE libbpp-raa::libbpp-raa)
endif()

enable_testing()
add_test(NAME test_bpp_raa COMMAND test_bpp_raa)
