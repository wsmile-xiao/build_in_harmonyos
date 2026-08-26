cmake_minimum_required(VERSION 3.15)
project(test_azure-storage-blobs-cpp CXX)

# Find the package via Conan-generated CMakeDeps
# cmake_file_name = "azure-storage-blobs" (from conanfile.py package_info)
find_package(azure-storage-blobs REQUIRED)

add_executable(test_azure-storage-blobs-cpp test.cpp)
# cmake_target_name = "Azure::azure-storage-blobs" (from conanfile.py package_info)
target_link_libraries(test_azure-storage-blobs-cpp Azure::azure-storage-blobs)
