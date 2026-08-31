cmake_minimum_required(VERSION 3.13)

project(test_apngasm CXX)

find_package(apngasm REQUIRED)
find_package(libpng REQUIRED)
find_package(zlib REQUIRED)

add_executable(test_apngasm src/main.cpp)
target_link_libraries(test_apngasm apngasm::apngasm libpng::libpng zlib::zlib)
# libpng recipe doesn't set cpp_info.includedirs, so add explicitly
target_include_directories(test_apngasm PRIVATE
    ${libpng_PACKAGE_FOLDER_RELEASE}/include
    ${zlib_PACKAGE_FOLDER_RELEASE}/include
)
set_target_properties(test_apngasm PROPERTIES CXX_STANDARD 20)

enable_testing()
add_test(NAME apngasm_version_test COMMAND test_apngasm)
