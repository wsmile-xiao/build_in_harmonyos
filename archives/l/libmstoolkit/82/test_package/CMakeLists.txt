cmake_minimum_required(VERSION 3.15)
project(libmstoolkit_test_package LANGUAGES CXX)

find_package(libmstoolkit CONFIG REQUIRED)

add_executable(test_libmstoolkit test_libmstoolkit.cpp)
target_link_libraries(test_libmstoolkit PRIVATE libmstoolkit::libmstoolkit)
target_compile_features(test_libmstoolkit PRIVATE cxx_std_11)

if(LIBMSTOOLKIT_BUILD_OHOS_TEST)
  add_executable(test_ohos_libmstoolkit test_ohos_libmstoolkit.cpp)
  target_link_libraries(test_ohos_libmstoolkit PRIVATE libmstoolkit::libmstoolkit)
  target_compile_features(test_ohos_libmstoolkit PRIVATE cxx_std_11)
endif()
