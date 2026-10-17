cmake_minimum_required(VERSION 3.15)
project(test_kysdk-ai-common CXX)

# Find the package via Conan-generated CMakeDeps (cmake_file_name = KysdkAiCommon)
find_package(KysdkAiCommon REQUIRED)

add_executable(test_kysdk-ai-common test.cpp)
target_link_libraries(test_kysdk-ai-common KysdkAiCommon::KysdkAiCommon)

enable_testing()
add_test(NAME test_kysdk-ai-common COMMAND test_kysdk-ai-common)
