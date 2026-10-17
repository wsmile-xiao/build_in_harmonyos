cmake_minimum_required(VERSION 3.15)
project(test_med C CXX)

find_package(medfile REQUIRED)
# MED's public header (med.h) includes <hdf5.h>, so consumers need HDF5's
# include path alongside the medfile target.
find_package(hdf5 REQUIRED)

add_executable(test_med test_med.cpp)

# The prebuilt/remote HDF5 package exposes an empty cpp_info.includedirs, so its
# CMake target does not carry the HDF5 include path. Reconstruct it from the
# package folder that CMakeDeps does expose (works on every platform).
if(DEFINED hdf5_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_med PRIVATE "${hdf5_PACKAGE_FOLDER_RELEASE}/include")
endif()

# On OHOS the test binary must run natively (the non-HAP loader cannot dlopen
# user-path .so). CMakeDeps only exposes the *shared* medC as `medfile::medfile`,
# so we link the packaged static archive libmedC.a directly and pull HDF5 (forced
# static) via its target, which transitively links libaec.a + libsz.a. The result
# is a fully static binary (only system libc/libz remain dynamic) that runs on OHOS.
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_include_directories(test_med PRIVATE "${med_PACKAGE_FOLDER_RELEASE}/include")
    target_link_libraries(test_med PRIVATE
        "${med_PACKAGE_FOLDER_RELEASE}/lib/libmedC.a"
        hdf5::hdf5)
else()
    target_link_libraries(test_med PRIVATE medfile::medfile hdf5::hdf5)
endif()
