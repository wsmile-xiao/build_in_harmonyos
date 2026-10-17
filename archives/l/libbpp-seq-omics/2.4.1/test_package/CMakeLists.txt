cmake_minimum_required(VERSION 3.15)
project(test_libbpp_seq_omics CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(_archives "")
foreach(_pair
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

add_executable(test_bpp_seq_omics test_bpp_seq_omics.cpp)
if(_archives)
  target_link_libraries(test_bpp_seq_omics PRIVATE ${_archives} m)
else()
  find_package(libbpp-seq-omics CONFIG REQUIRED)
  target_link_libraries(test_bpp_seq_omics PRIVATE libbpp-seq-omics::libbpp-seq-omics)
endif()

enable_testing()
add_test(NAME test_bpp_seq_omics COMMAND test_bpp_seq_omics)
