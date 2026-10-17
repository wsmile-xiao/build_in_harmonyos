cmake_minimum_required(VERSION 3.15)
project(test_libbpp_popgen CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

message(STATUS "libbpp-popgen package folder: ${LIBBPP_POPGEN_PACKAGE_FOLDER}")
message(STATUS "libbpp-seq    package folder: ${LIBBPP_SEQ_PACKAGE_FOLDER}")

add_executable(test_bpp_popgen test_bpp_popgen.cpp)

set(_POPGEN_LIB "${LIBBPP_POPGEN_PACKAGE_FOLDER}/lib/libbpp-popgen.a")
set(_SEQ_LIB   "${LIBBPP_SEQ_PACKAGE_FOLDER}/lib/libbpp-seq.a")
set(_CORE_LIB  "${LIBBPP_SEQ_PACKAGE_FOLDER}/lib/libbpp-core.a")

if(EXISTS "${_POPGEN_LIB}" AND EXISTS "${_SEQ_LIB}" AND EXISTS "${_CORE_LIB}")
  # Pin the static archives by absolute path: the consumer then has no runtime
  # shared-object dependency at all (upstream installs a static+shared pair,
  # and the shared object is not needed to verify the public API).
  target_include_directories(test_bpp_popgen PRIVATE
    "${LIBBPP_POPGEN_PACKAGE_FOLDER}/include"
    "${LIBBPP_SEQ_PACKAGE_FOLDER}/include")
  target_link_libraries(test_bpp_popgen PRIVATE
    "${_POPGEN_LIB}" "${_SEQ_LIB}" "${_CORE_LIB}")
  message(STATUS "test_bpp_popgen: linking the shipped static archives")
else()
  # Fallback for a shared-only package: use the Conan-generated target.
  message(STATUS "test_bpp_popgen: static archives absent, using the Conan target")
  find_package(libbpp-popgen CONFIG REQUIRED)
  target_link_libraries(test_bpp_popgen PRIVATE libbpp-popgen::libbpp-popgen)
endif()

if(UNIX)
  target_link_libraries(test_bpp_popgen PRIVATE m)
endif()

enable_testing()
add_test(NAME test_bpp_popgen COMMAND test_bpp_popgen)
