cmake_minimum_required(VERSION 3.15)
project(test_azure-identity-cpp CXX)

# Use the Conan-generated config (cmake_file_name="azure-identity") so that
# transitive deps (azure-core/openssl) are wired through CMakeDeps.
# Explicitly find azure-core and openssl for transitive include paths.
find_package(azure-identity REQUIRED)
find_package(azure-core REQUIRED)
find_package(openssl REQUIRED)

add_executable(test_azure-identity-cpp test.cpp)
target_link_libraries(test_azure-identity-cpp
    Azure::azure-identity
    Azure::azure-core
    openssl::openssl)

enable_testing()
add_test(NAME test_azure-identity-cpp COMMAND test_azure-identity-cpp)