cmake_minimum_required(VERSION 3.15)
project(test_easyflash C)

# Find the package via Conan-generated CMakeDeps
find_package(easyflash REQUIRED)

add_executable(test_easyflash test.c ef_port_ram.c)
target_link_libraries(test_easyflash PRIVATE easyflash::easyflash)

# HarmonyOS-specific test: binary blob round-trip / NV persistence / defaults
add_executable(ohos_env_test ohos_env_test.c ef_port_ram.c)
target_link_libraries(ohos_env_test PRIVATE easyflash::easyflash)

enable_testing()
add_test(NAME test_easyflash COMMAND test_easyflash)
add_test(NAME ohos_env_test COMMAND ohos_env_test)