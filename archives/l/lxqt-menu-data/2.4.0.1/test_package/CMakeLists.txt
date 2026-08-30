cmake_minimum_required(VERSION 3.15)
project(test_lxqt-menu-data C)

# Find the package via Conan-generated CMakeDeps
find_package(lxqt-menu-data REQUIRED)

add_executable(test_lxqt-menu-data test.c)

# Pass the installed share/ dir so test.c can verify data files (R34)
if(DEFINED MENU_DATA_DIR)
    target_compile_definitions(test_lxqt-menu-data PRIVATE
        MENU_DATA_DIR="${MENU_DATA_DIR}")
endif()

enable_testing()
add_test(NAME test_lxqt-menu-data COMMAND test_lxqt-menu-data)