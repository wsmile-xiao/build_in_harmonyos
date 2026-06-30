cmake_minimum_required(VERSION 3.15)
project(test_perl-plack C)

# Find the package via Conan-generated CMakeDeps
find_package(perl-plack REQUIRED)

add_executable(test_perl-plack test.c)
target_link_libraries(test_perl-plack perl-plack::perl-plack)

enable_testing()
add_test(NAME test_perl-plack COMMAND test_perl-plack)
