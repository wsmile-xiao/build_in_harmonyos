cmake_minimum_required(VERSION 3.15)
project(test_azure-storage-common-cpp C CXX)

# Find the package via Conan-generated CMakeDeps
# cmake_file_name = "azure-storage-common" (from conanfile.py package_info)
find_package(azure-storage-common REQUIRED)

add_executable(test_azure-storage-common-cpp test.cpp)
# cmake_target_name = "Azure::azure-storage-common" (from conanfile.py package_info)
target_link_libraries(test_azure-storage-common-cpp Azure::azure-storage-common)

enable_testing()
add_test(NAME test_azure-storage-common-cpp COMMAND test_azure-storage-common-cpp)