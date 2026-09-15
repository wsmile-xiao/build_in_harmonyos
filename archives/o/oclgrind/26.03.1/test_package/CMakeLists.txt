cmake_minimum_required(VERSION 3.15)
project(test_oclgrind C)

find_package(oclgrind REQUIRED)
find_package(opencl-headers REQUIRED)

add_executable(test_oclgrind test_oclgrind.c)
target_link_libraries(test_oclgrind oclgrind::oclgrind opencl-headers::opencl-headers)

# The OpenCL entry points (clGetPlatformIDs/...) live in the oclgrind
# runtime library (liboclgrind-rt, SONAME libOpenCL.so), not in the headers
# package. The oclgrind::oclgrind interface alone left them unresolved with
# ld.lld on OHOS, so bind the runtime file explicitly from the package folder.
if(DEFINED OCLGRIND_PACKAGE_FOLDER)
  find_library(OCLGRIND_RT_LIB NAMES oclgrind-rt OpenCL
    PATHS "${OCLGRIND_PACKAGE_FOLDER}/lib" "${OCLGRIND_PACKAGE_FOLDER}/lib64"
    NO_DEFAULT_PATH)
endif()
if(NOT OCLGRIND_RT_LIB)
  find_library(OCLGRIND_RT_LIB NAMES oclgrind-rt OpenCL)
endif()
if(OCLGRIND_RT_LIB)
  target_link_libraries(test_oclgrind "${OCLGRIND_RT_LIB}")
else()
  message(WARNING "oclgrind runtime library (oclgrind-rt/OpenCL) not found; cl* symbols may stay unresolved")
endif()

enable_testing()
add_test(NAME test_oclgrind COMMAND test_oclgrind)
