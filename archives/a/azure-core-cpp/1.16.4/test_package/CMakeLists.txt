cmake_minimum_required(VERSION 3.15)
project(test_azure-core-cpp CXX)

# Use the Conan-generated config (cmake_file_name="azure-core") so that
# transitive deps (curl/openssl) are wired through CMakeDeps, instead of
# the upstream azure-core-cppConfig.cmake whose find_dependency(OpenSSL)
# uses the system FindOpenSSL module (absent on OHOS).
find_package(azure-core REQUIRED)

add_executable(test_azure-core-cpp test.cpp)
target_link_libraries(test_azure-core-cpp Azure::azure-core)

enable_testing()
add_test(NAME test_azure-core-cpp COMMAND test_azure-core-cpp)