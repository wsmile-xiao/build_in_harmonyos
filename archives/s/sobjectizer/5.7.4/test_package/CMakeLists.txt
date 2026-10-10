cmake_minimum_required(VERSION 3.15)
project(test_sobjectizer CXX)

# Find the packaged library through Conan-generated CMakeDeps files.
# The recipe declares cmake_file_name "sobjectizer", so this resolves to the
# exported sobjectizer-config.cmake shipped by upstream's install rules.
find_package(sobjectizer CONFIG REQUIRED)

find_package(Threads REQUIRED)

# Part 1/2/3: consumer test driven through the packaged library.
# sobjectizer::SharedLib is the exported target name of libso (see the
# recipe's cmake_target_name / upstream's EXPORT_NAME SharedLib).
add_executable(test_sobjectizer test_sobjectizer.cpp)
target_link_libraries(test_sobjectizer PRIVATE sobjectizer::SharedLib)
target_link_libraries(test_sobjectizer PRIVATE Threads::Threads)

# A second, independent consumer that links the STATIC library instead, proving
# both package_type variants produced by the recipe are usable.
add_executable(test_sobjectizer_static test_sobjectizer_static.cpp)
target_link_libraries(test_sobjectizer_static PRIVATE sobjectizer::StaticLib)
target_link_libraries(test_sobjectizer_static PRIVATE Threads::Threads)
