cmake_minimum_required(VERSION 3.15)
project(test_libabw CXX)
set(CMAKE_VERBOSE_MAKEFILE ON)

find_package(libabw REQUIRED)

add_executable(test_libabw test.cpp)
target_compile_features(test_libabw PRIVATE cxx_std_11)
target_link_libraries(test_libabw libabw::libabw)

# librevenge 制品包（旧配方发布）的 cpp_info 缺 includedirs，消费者 target
# 接口不完整；此处用 CMakeDeps 数据变量显式补齐路径（CI 与设备一致）。
if(DEFINED librevenge_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_libabw PRIVATE "${librevenge_PACKAGE_FOLDER_RELEASE}/include/librevenge-0.0")
    target_link_directories(test_libabw PRIVATE "${librevenge_PACKAGE_FOLDER_RELEASE}/lib")
    target_link_libraries(test_libabw revenge-0.0 revenge-generators-0.0)
endif()
if(DEFINED LibXml2_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_libabw PRIVATE "${LibXml2_PACKAGE_FOLDER_RELEASE}/include/libxml2")
    target_link_directories(test_libabw PRIVATE "${LibXml2_PACKAGE_FOLDER_RELEASE}/lib")
    target_link_libraries(test_libabw xml2)
endif()
if(DEFINED zlib_PACKAGE_FOLDER_RELEASE)
    target_link_directories(test_libabw PRIVATE "${zlib_PACKAGE_FOLDER_RELEASE}/lib")
    target_link_libraries(test_libabw z)
endif()

enable_testing()
add_test(NAME test_libabw COMMAND test_libabw)
