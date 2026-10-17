cmake_minimum_required(VERSION 3.15)
project(test_qpid_proton C)

# The package ships its own lib/cmake/Proton config (ProtonConfig.cmake), and
# conan's CMakeDeps writes an equivalent one into the generator folder; either
# way find_package(Proton) resolves to the installed package.
find_package(Proton REQUIRED)

add_executable(test_qpid_proton test_qpid_proton.c)
target_link_libraries(test_qpid_proton PRIVATE Proton::qpid-proton)

enable_testing()
add_test(NAME test_qpid_proton COMMAND test_qpid_proton)
