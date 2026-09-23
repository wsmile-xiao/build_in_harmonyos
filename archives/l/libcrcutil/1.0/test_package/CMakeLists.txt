cmake_minimum_required(VERSION 3.15)
project(libcrcutil_test_package LANGUAGES CXX)

find_package(libcrcutil CONFIG REQUIRED)

add_executable(test_libcrcutil test_libcrcutil.cpp)
target_link_libraries(test_libcrcutil PRIVATE libcrcutil::libcrcutil)
target_compile_features(test_libcrcutil PRIVATE cxx_std_11)

add_executable(test_vectors test_vectors.cpp)
target_link_libraries(test_vectors PRIVATE libcrcutil::libcrcutil)
target_compile_features(test_vectors PRIVATE cxx_std_11)

add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos PRIVATE libcrcutil::libcrcutil)
target_compile_features(test_ohos PRIVATE cxx_std_11)
