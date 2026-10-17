cmake_minimum_required(VERSION 3.15)
project(test_ncnn CXX)

find_package(ncnn CONFIG REQUIRED)
add_executable(test_ncnn test_ncnn.cpp)
target_link_libraries(test_ncnn PRIVATE ncnn)

# Upstream ncnn installs headers under <prefix>/include/ncnn and its exported
# target propagates INTERFACE_INCLUDE_DIRECTORIES=<prefix>/include/ncnn, so
# consumers include headers as <ncnn/mat.h> only when <prefix>/include is on
# the include path.  Add that root explicitly for the smoke test.
get_target_property(NCNN_INCLUDE_DIR ncnn INTERFACE_INCLUDE_DIRECTORIES)
get_filename_component(NCNN_INCLUDE_ROOT "${NCNN_INCLUDE_DIR}" DIRECTORY)
target_include_directories(test_ncnn PRIVATE "${NCNN_INCLUDE_ROOT}")
