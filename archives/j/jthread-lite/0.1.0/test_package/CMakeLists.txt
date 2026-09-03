cmake_minimum_required(VERSION 3.15)
project(test_jthread_lite LANGUAGES CXX)

# Find the package via Conan-generated CMakeDeps
find_package(jthread-lite REQUIRED)

add_executable(test_jthread_lite test.cpp)
target_compile_features(test_jthread_lite PRIVATE cxx_std_17)
target_link_libraries(test_jthread_lite PRIVATE nonstd::jthread-lite)

# std::thread is used under the hood by nonstd::jthread
find_package(Threads REQUIRED)
target_link_libraries(test_jthread_lite PRIVATE Threads::Threads)

enable_testing()
add_test(NAME test_jthread_lite COMMAND test_jthread_lite)