cmake_minimum_required(VERSION 3.15)
project(test_level_zero_gpu_raytracing LANGUAGES CXX)

# Provided by the Conan package through CMakeDeps.
find_package(ze_raytracing CONFIG REQUIRED)

add_executable(test_level_zero_gpu_raytracing test.cpp)
target_compile_features(test_level_zero_gpu_raytracing PRIVATE cxx_std_17)
target_link_libraries(test_level_zero_gpu_raytracing PRIVATE ze_raytracing::ze_raytracing)

# The test resolves exported symbols with dlsym at runtime, which mirrors how
# the Level Zero loader picks the library up.
find_package(Threads REQUIRED)
target_link_libraries(test_level_zero_gpu_raytracing PRIVATE Threads::Threads ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_level_zero_gpu_raytracing COMMAND test_level_zero_gpu_raytracing)
