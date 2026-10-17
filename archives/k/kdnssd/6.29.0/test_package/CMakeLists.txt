cmake_minimum_required(VERSION 3.15)
project(test_kdnssd CXX)

# Find the package via Conan-generated CMakeDeps
find_package(KF6DNSSD REQUIRED)

add_executable(test_kdnssd test_kdnssd.cpp)
target_link_libraries(test_kdnssd KF6::DNSSD Qt6::Core)

# HarmonyOS-specific test asserting the OHOS platform adaptation path
# (dummy backend behavior: isAvailable()==Unsupported, empty host name,
# synchronous finished() from startBrowse(), empty service list).
add_executable(test_kdnssd_ohos test_kdnssd_ohos.cpp)
target_link_libraries(test_kdnssd_ohos KF6::DNSSD Qt6::Core)

enable_testing()
add_test(NAME test_kdnssd COMMAND test_kdnssd)
add_test(NAME test_kdnssd_ohos COMMAND test_kdnssd_ohos)
