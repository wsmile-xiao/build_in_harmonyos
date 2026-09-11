cmake_minimum_required(VERSION 3.15)
project(test_msfconsole C)

# msfconsole is an application package, not a library.
# No find_package() or target_link_libraries() needed.
# The test binary invokes the package's installed tools via system().

add_executable(test_msfconsole test.c)

enable_testing()
add_test(NAME test_msfconsole COMMAND test_msfconsole)
