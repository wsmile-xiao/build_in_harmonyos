cmake_minimum_required(VERSION 3.16)
project(test_vcflib CXX)

# vcflib's public headers need htslib/zlib/xz/bzip2 headers on the include
# path (Variant.h -> tabix.hpp -> htslib/bgzf.h), and the static libvcflib.a
# references their archives. Resolve each dependency explicitly so the
# consumer test compiles and links deterministically.
#
# The zlib/bzip2 (and to a lesser extent libdeflate) CMake target spelling is
# NOT stable across the build environments. These recipes advertise only
# cpp_info.libs (and libdeflate advertises cmake_target_name="libdeflate::")
# with no stable per-package cmake_target_name, so CMakeDeps derives the
# imported target name from its own name-resolution rules, which differ
# between the official CI worker (zlib::zlib / bzip2::bzip2) and the HarmonyOS
# aarch64 preflight device (ZLIB::ZLIB / BZip2::BZip2 / libdeflate::libdeflate_static).
# We therefore probe BOTH spellings and link whatever target actually exists,
# instead of hard-coding one spelling that only one environment produces.
find_package(vcflib REQUIRED)
find_package(htslib REQUIRED CONFIG)
find_package(xz REQUIRED CONFIG)

# --- zlib: accept either generated target spelling -------------------------
find_package(zlib QUIET CONFIG)
if(NOT TARGET zlib::zlib)
  find_package(ZLIB QUIET)
endif()
if(TARGET zlib::zlib)
  set(_vcflib_zlib_target zlib::zlib)
elseif(TARGET ZLIB::ZLIB)
  set(_vcflib_zlib_target ZLIB::ZLIB)
else()
  message(FATAL_ERROR "test_vcflib: zlib CMake target not found (tried zlib::zlib, ZLIB::ZLIB)")
endif()

# --- bzip2: accept either generated target spelling ------------------------
find_package(bzip2 QUIET CONFIG)
if(NOT TARGET bzip2::bzip2)
  find_package(BZip2 QUIET)
endif()
if(TARGET bzip2::bzip2)
  set(_vcflib_bzip2_target bzip2::bzip2)
elseif(TARGET BZip2::BZip2)
  set(_vcflib_bzip2_target BZip2::BZip2)
else()
  message(FATAL_ERROR "test_vcflib: bzip2 CMake target not found (tried bzip2::bzip2, BZip2::BZip2)")
endif()

# --- libdeflate: accept base or the static component target ---------------
find_package(libdeflate QUIET CONFIG)
if(TARGET libdeflate::libdeflate)
  set(_vcflib_libdeflate_target libdeflate::libdeflate)
elseif(TARGET libdeflate::libdeflate_static)
  set(_vcflib_libdeflate_target libdeflate::libdeflate_static)
else()
  message(FATAL_ERROR "test_vcflib: libdeflate CMake target not found")
endif()

add_executable(test_vcflib test_vcflib.cpp)
target_link_libraries(test_vcflib PRIVATE
    vcflib::vcflib
    htslib::htslib
    ${_vcflib_zlib_target}
    xz::xz
    ${_vcflib_bzip2_target}
    ${_vcflib_libdeflate_target}
)

# Place the VCF fixture next to the test binary so the runtime test can
# resolve it via a relative path.
add_custom_command(TARGET test_vcflib POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_CURRENT_SOURCE_DIR}/sample.vcf
        $<TARGET_FILE_DIR:test_vcflib>/sample.vcf
)
