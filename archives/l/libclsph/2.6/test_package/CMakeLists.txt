cmake_minimum_required(VERSION 3.15)
project(test_libclsph CXX)

# Find the package via Conan-generated CMakeDeps (ocl-icd is a transitive
# dependency of libclsph::libclsph — no explicit find_package needed).
find_package(libclsph REQUIRED)

# 1) Consumer verification: uses only the installed public headers/API.
add_executable(consumer_clsph consumer_clsph.cpp)
target_link_libraries(consumer_clsph libclsph::libclsph)
target_compile_definitions(consumer_clsph PRIVATE USE_LOCAL_CL_HPP=1)
target_compile_features(consumer_clsph PRIVATE cxx_std_11)

# 2) HarmonyOS-specific test: OHOS OpenCL stack end-to-end via exported
#    cl.hpp bindings (platform enumerate + SPH kernel compile + execute).
add_executable(ohos_sph_test ohos_sph_test.cpp)
target_link_libraries(ohos_sph_test libclsph::libclsph)
target_compile_definitions(ohos_sph_test PRIVATE USE_LOCAL_CL_HPP=1)
target_compile_features(ohos_sph_test PRIVATE cxx_std_11)

enable_testing()
add_test(NAME consumer_clsph COMMAND consumer_clsph)
add_test(NAME ohos_sph_test COMMAND ohos_sph_test)
