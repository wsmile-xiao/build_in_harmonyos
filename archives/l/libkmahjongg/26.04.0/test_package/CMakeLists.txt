cmake_minimum_required(VERSION 3.15)
project(test_libkmahjongg CXX)

# Load Qt6 first (needed by KF6 cmake targets)
find_package(Qt6 REQUIRED COMPONENTS Core Gui)
# Qt6Svg is a separate Conan package; find it as its own config-file package.
find_package(Qt6Svg REQUIRED)
find_package(KF6ConfigWidgets REQUIRED)
find_package(KMahjongglib6 REQUIRED)

add_executable(test_libkmahjongg test.cpp)
target_link_libraries(test_libkmahjongg KMahjongglib6 Qt6::Gui)

enable_testing()
add_test(NAME test_libkmahjongg COMMAND test_libkmahjongg)
