cmake_minimum_required(VERSION 3.15)
project(test_knotifications CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6Notifications REQUIRED)

add_executable(test_knotifications test.cpp)
target_link_libraries(test_knotifications KF6::Notifications)

# CMake has no native HarmonyOS platform module, so its generic RPATH handling
# is disabled. Add the Conan runtime directories to this executable directly.
foreach(runtime_lib_dir IN LISTS CONAN_RUNTIME_LIB_DIRS)
    target_link_options(test_knotifications PRIVATE "-Wl,-rpath,${runtime_lib_dir}")
endforeach()
target_link_options(test_knotifications PRIVATE "-Wl,--disable-new-dtags")

enable_testing()
add_test(NAME test_knotifications COMMAND test_knotifications)
