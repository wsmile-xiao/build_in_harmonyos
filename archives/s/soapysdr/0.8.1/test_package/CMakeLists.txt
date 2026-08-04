cmake_minimum_required(VERSION 3.10)
project(test_soapysdr CXX)

# Find the package via Conan-generated CMakeDeps
find_package(SoapySDR REQUIRED)

add_executable(test_soapysdr test.cpp)
target_link_libraries(test_soapysdr SoapySDR::SoapySDR)

enable_testing()
add_test(NAME test_soapysdr COMMAND test_soapysdr)