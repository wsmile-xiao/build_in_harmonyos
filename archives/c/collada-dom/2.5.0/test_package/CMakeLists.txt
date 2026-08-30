cmake_minimum_required(VERSION 3.15)
project(test_collada_dom CXX)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=collada_dom)
find_package(collada_dom REQUIRED)

add_executable(test_collada_dom src/test.cpp)
# CMakeDeps generates a plain `collada_dom` target (no namespace) because the
# recipe declares cmake_target_name="collada_dom".
target_link_libraries(test_collada_dom collada_dom)
target_compile_features(test_collada_dom PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_collada_dom COMMAND test_collada_dom)