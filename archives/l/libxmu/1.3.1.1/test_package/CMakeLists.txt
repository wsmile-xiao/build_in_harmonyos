cmake_minimum_required(VERSION 3.15)
project(test_libxmu C)

# Find the package via Conan-generated CMakeDeps
find_package(libxmu REQUIRED)

# test.c calls XmuCompareISOLatin1(), exported by the libXmuu component
# (the Xt-independent subset of libXmu).
add_executable(test_libxmu test.c)
target_link_libraries(test_libxmu libxmu::Xmuu)

# test_ohos.c calls XmuReadBitmapDataFromFile(), which lives in the Xt-linked
# libXmu component, and asserts the HarmonyOS degradation paths (rule12).
add_executable(test_libxmu_ohos test_ohos.c)
target_link_libraries(test_libxmu_ohos libxmu::Xmu)

enable_testing()
add_test(NAME test_libxmu COMMAND test_libxmu)
add_test(NAME test_libxmu_ohos COMMAND test_libxmu_ohos)
