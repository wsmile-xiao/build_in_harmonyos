cmake_minimum_required(VERSION 3.15)
project(test_libheif_openh264 CXX)

# 被测包的交付面走标准 CMakeDeps：配方 package_info() 的 cmake_file_name=libheif，
# 目标名 libheif::libheif（宿主 libheif.so）。
find_package(libheif REQUIRED)

# 依赖包 openh264 由 conanfile.py 的 generate() 解析成绝对路径下发——理由见该文件 docstring
# （CMakeDeps 对未被直接依赖 re-export 的传递依赖不写 includedirs/libs）。
if(NOT OPENH264_INCLUDE_DIRS OR NOT OPENH264_LIBDIR OR NOT OPENH264_LIBNAME)
  message(FATAL_ERROR "缺少 OPENH264_INCLUDE_DIRS/OPENH264_LIBDIR/OPENH264_LIBNAME（conanfile.py generate() 未下发）")
endif()
message(STATUS "openh264: include=${OPENH264_INCLUDE_DIRS} libdir=${OPENH264_LIBDIR} lib=${OPENH264_LIBNAME}")

add_executable(test_libheif_openh264 test_libheif_openh264.cpp)
target_link_libraries(test_libheif_openh264 PRIVATE libheif::libheif)
target_include_directories(test_libheif_openh264 PRIVATE ${OPENH264_INCLUDE_DIRS})
target_link_directories(test_libheif_openh264 PRIVATE ${OPENH264_LIBDIR})
target_link_libraries(test_libheif_openh264 PRIVATE ${OPENH264_LIBNAME})

enable_testing()
add_test(NAME test_libheif_openh264 COMMAND test_libheif_openh264)
