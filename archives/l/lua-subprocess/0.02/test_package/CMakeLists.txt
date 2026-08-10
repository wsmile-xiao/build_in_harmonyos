cmake_minimum_required(VERSION 3.15)
project(test_subprocess C)

# Find lua via Conan's CMakeDeps generator
find_package(lua REQUIRED)

add_executable(test_subprocess test_subprocess.c)

# Link against lua and export dynamic symbols so subprocess.so can resolve them
target_link_libraries(test_subprocess lua::lua)
target_link_options(test_subprocess PRIVATE "-rdynamic")
