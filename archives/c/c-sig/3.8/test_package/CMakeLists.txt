cmake_minimum_required(VERSION 3.15)
project(test_c_sig LANGUAGES CXX)

# sigc++-3 / sigc-3.0 match upstream config names (see package_info)
find_package(sigc++-3 REQUIRED CONFIG)

add_executable(test_c_sig test.cpp)
target_link_libraries(test_c_sig PRIVATE sigc-3.0)
target_compile_features(test_c_sig PRIVATE cxx_std_17)

add_executable(test_c_sig_observer test_observer.cpp)
target_link_libraries(test_c_sig_observer PRIVATE sigc-3.0)
target_compile_features(test_c_sig_observer PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_c_sig COMMAND test_c_sig)
add_test(NAME test_c_sig_observer COMMAND test_c_sig_observer)
