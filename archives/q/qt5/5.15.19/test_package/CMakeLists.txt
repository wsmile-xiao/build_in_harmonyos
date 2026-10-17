cmake_minimum_required(VERSION 3.15)
project(test_qt5 C CXX)

# Find Qt5 through Conan-generated CMakeDeps
find_package(qt5 REQUIRED COMPONENTS Qt5Core Qt5Network)

# Core/Network test - comprehensive Qt5Core/Qt5Network API test
add_executable(test_qt5_all test_qt5_all.cpp)
target_link_libraries(test_qt5_all Qt5::Core Qt5::Network)
target_compile_features(test_qt5_all PUBLIC cxx_std_17)

enable_testing()
add_test(NAME test_qt5_all COMMAND test_qt5_all)
