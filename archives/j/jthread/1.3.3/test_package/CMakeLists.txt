cmake_minimum_required(VERSION 3.15)
project(test_jthread LANGUAGES CXX)

find_package(jthread CONFIG REQUIRED)

add_executable(test_lifecycle test_lifecycle.cpp)
target_compile_features(test_lifecycle PRIVATE cxx_std_11)
target_link_libraries(test_lifecycle PRIVATE jthread::jthread)

add_executable(test_return_value test_return_value.cpp)
target_compile_features(test_return_value PRIVATE cxx_std_11)
target_link_libraries(test_return_value PRIVATE jthread::jthread)

add_executable(test_multiple_threads test_multiple_threads.cpp)
target_compile_features(test_multiple_threads PRIVATE cxx_std_11)
target_link_libraries(test_multiple_threads PRIVATE jthread::jthread)

enable_testing()
add_test(NAME lifecycle COMMAND test_lifecycle)
add_test(NAME return_value COMMAND test_return_value)
add_test(NAME multiple_threads COMMAND test_multiple_threads)
