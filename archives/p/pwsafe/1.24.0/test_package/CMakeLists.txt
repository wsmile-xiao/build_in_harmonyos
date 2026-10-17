cmake_minimum_required(VERSION 3.15)
project(test_pwsafe C)

# pwsafe is an application package — we find the binary via bindirs,
# not via a linkable library target.
# The conanrun environment adds the package's bin/ to PATH.

add_executable(test_pwsafe test_pwsafe.c)

enable_testing()
add_test(NAME test_pwsafe COMMAND test_pwsafe)
