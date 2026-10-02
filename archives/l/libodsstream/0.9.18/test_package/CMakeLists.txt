cmake_minimum_required(VERSION 3.15)
project(test_odsstream CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

# Order matters: OdsStreamTargets' INTERFACE_LINK_LIBRARIES references
# Qt6::Xml/Qt6::Gui/QuaZip::QuaZip/zlib::zlib, so these targets must exist
# before find_package(OdsStream) includes the targets file.
find_package(Qt6 COMPONENTS Core Gui Xml REQUIRED)
find_package(QuaZip-Qt6 REQUIRED)
find_package(zlib REQUIRED)
find_package(OdsStream REQUIRED)

add_executable(test_odsstream test_odsstream.cpp)
target_link_libraries(test_odsstream PRIVATE OdsStream::Core)
# Upstream's INTERFACE_INCLUDE_DIRECTORIES is include/odsstream (headers
# are installed flat there), but the sources use <odsstream/xxx.h> — add
# the package include root too.
target_include_directories(test_odsstream PRIVATE ${OdsStream_INCLUDE_DIR})
get_filename_component(_ods_pkg_root "${OdsStream_DIR}" PATH)
get_filename_component(_ods_pkg_root "${_ods_pkg_root}" PATH)
get_filename_component(_ods_pkg_root "${_ods_pkg_root}" PATH)
target_include_directories(test_odsstream PRIVATE "${_ods_pkg_root}/include")
enable_testing()
add_test(NAME odsstream_roundtrip COMMAND test_odsstream)
