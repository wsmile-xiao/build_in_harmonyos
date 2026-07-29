cmake_minimum_required(VERSION 3.15)
project(test_alembic CXX)

find_package(alembic REQUIRED)

add_executable(test_alembic test_alembic.cpp)
target_link_libraries(test_alembic alembic::alembic)
# C++ standard is provided by the Conan CMakeToolchain (profile cppstd);
# target_compile_features is avoided because CMake 4.x cannot identify the
# OHOS clang, leaving CMAKE_CXX_COMPILE_FEATURES empty.

enable_testing()
add_test(NAME test_alembic COMMAND test_alembic)
