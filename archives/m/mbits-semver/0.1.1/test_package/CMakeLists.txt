cmake_minimum_required(VERSION 3.15)
project(test_mbits-semver CXX)

# Find the package via Conan-generated CMakeDeps
find_package(mbits-semver REQUIRED)

add_executable(test_mbits-semver test.cpp)
target_link_libraries(test_mbits-semver mbits-semver::mbits-semver)
target_compile_features(test_mbits-semver PRIVATE cxx_std_17)

# HarmonyOS 专项测试：语义矩阵验证（独立于上游与消费者用例）
add_executable(ohos-semver-test ohos-test.cpp)
target_link_libraries(ohos-semver-test mbits-semver::mbits-semver)
target_compile_features(ohos-semver-test PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_mbits-semver COMMAND test_mbits-semver)
add_test(NAME ohos-semver-test COMMAND ohos-semver-test)
