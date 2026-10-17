cmake_minimum_required(VERSION 3.15)
project(test_libbpp_seq CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Upstream package configs (headers + target info).
find_package(bpp-seq CONFIG QUIET)
find_package(bpp-core CONFIG QUIET)
if(NOT bpp-core_FOUND)
  find_package(libbpp-core CONFIG QUIET)
endif()

add_executable(test_bpp_seq test_bpp_seq.cpp)

# OHOS/musl loader cannot resolve the installed libbpp-seq.so: its DT_NEEDED
# is the slash-containing build-tree path
# "../bpp-core-prefix/lib/libbpp-core.so", which the loader treats as a
# literal path (LD_LIBRARY_PATH/RUNPATH are not consulted for slash entries).
# Previous cycle scanned CMAKE_PREFIX_PATH for the static archives, but the
# test_package toolchain never puts the tested package folder there, so it
# always fell back to the shared target and failed at runtime.
# New route: conanfile generate() injects the absolute tested package folder
# as LIBBPP_SEQ_PACKAGE_FOLDER; pin both static archives by absolute path so
# the consumer has zero runtime .so dependency. Same API, same 8 CHECKs.
set(_BPP_STATIC_DONE FALSE)
if(DEFINED LIBBPP_SEQ_PACKAGE_FOLDER
    AND EXISTS "${LIBBPP_SEQ_PACKAGE_FOLDER}/lib/libbpp-seq.a"
    AND EXISTS "${LIBBPP_SEQ_PACKAGE_FOLDER}/lib/libbpp-core.a")
  target_include_directories(test_bpp_seq PRIVATE "${LIBBPP_SEQ_PACKAGE_FOLDER}/include")
  target_link_libraries(test_bpp_seq PRIVATE
    "${LIBBPP_SEQ_PACKAGE_FOLDER}/lib/libbpp-seq.a"
    "${LIBBPP_SEQ_PACKAGE_FOLDER}/lib/libbpp-core.a")
  if(UNIX)
    target_link_libraries(test_bpp_seq PRIVATE m)
  endif()
  set(_BPP_STATIC_DONE TRUE)
  message(STATUS "test_bpp_seq links static archives in ${LIBBPP_SEQ_PACKAGE_FOLDER}/lib")
endif()
if(NOT _BPP_STATIC_DONE)
  message(STATUS "test_bpp_seq: static archives not found, falling back to targets")
  if(TARGET bpp-seq-static)
    target_link_libraries(test_bpp_seq PRIVATE bpp-seq-static)
  elseif(bpp-seq_FOUND)
    target_link_libraries(test_bpp_seq PRIVATE bpp-seq-shared)
  else()
    find_package(libbpp-seq CONFIG REQUIRED)
    target_link_libraries(test_bpp_seq PRIVATE libbpp-seq::libbpp-seq)
  endif()
  if(TARGET bpp-core-static)
    target_link_libraries(test_bpp_seq PRIVATE bpp-core-static)
  endif()
endif()
unset(_BPP_STATIC_DONE)
unset(_prefix)

enable_testing()
add_test(NAME test_bpp_seq COMMAND test_bpp_seq)
