cmake_minimum_required(VERSION 3.16)
project(test_qcoro_core CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# qtbase on ohpcd ships Qt's own Qt6Config.cmake (cmake_find_mode=none), so Qt6
# must be found explicitly first: QCoro6::Core links Qt6::Core. Qt6_DIR comes
# from the toolchain.
find_package(Qt6 COMPONENTS Core CONFIG REQUIRED)
find_package(QCoro6 REQUIRED COMPONENTS Core)

add_executable(test_qcoro_core test_qcoro_core.cpp)

target_link_libraries(test_qcoro_core PRIVATE QCoro6::Core)

enable_testing()
add_test(NAME test_qcoro_core COMMAND test_qcoro_core)
