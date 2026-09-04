cmake_minimum_required(VERSION 3.15)
project(test_libsvm CXX)

find_package(libsvm REQUIRED)

add_executable(test_libsvm test_libsvm.cpp)
target_link_libraries(test_libsvm libsvm::libsvm)

add_executable(test_libsvm_ohos test_libsvm_ohos.cpp)
target_link_libraries(test_libsvm_ohos libsvm::libsvm)

enable_testing()
add_test(NAME test_libsvm COMMAND test_libsvm)
add_test(NAME test_libsvm_ohos COMMAND test_libsvm_ohos)
