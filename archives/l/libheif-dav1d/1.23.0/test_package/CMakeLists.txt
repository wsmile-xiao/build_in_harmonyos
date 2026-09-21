cmake_minimum_required(VERSION 3.15)
project(test_libheif_dav1d C)

find_package(libheif REQUIRED)

add_executable(test_libheif_dav1d test.c)
target_link_libraries(test_libheif_dav1d libheif::libheif)

# 插件产物路径由 test_package/conanfile.py 的 generate() 用被测包真实
# package_folder 注入（cache 变量 HEIF_PLUGIN_FILE）。
# 不从导入目标 IMPORTED_LOCATION 反推：实测该属性取不到值，会退化成
# "/libheif/libheif-dav1d.so" 这种假路径，让"产物是否存在"的断言失去意义。
if(NOT DEFINED HEIF_PLUGIN_FILE)
    message(FATAL_ERROR
        "HEIF_PLUGIN_FILE 未注入：test_package/conanfile.py 的 generate() 必须设置它")
endif()
message(STATUS "libheif-dav1d plugin under test: ${HEIF_PLUGIN_FILE}")
target_compile_definitions(test_libheif_dav1d PRIVATE HEIF_PLUGIN_FILE="${HEIF_PLUGIN_FILE}")

enable_testing()
add_test(NAME test_libheif_dav1d COMMAND test_libheif_dav1d)
