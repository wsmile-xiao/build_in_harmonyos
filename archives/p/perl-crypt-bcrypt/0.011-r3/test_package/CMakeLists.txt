cmake_minimum_required(VERSION 3.15)
project(test_crypt_bcrypt C)

# Find the package via Conan-generated CMakeDeps
find_package(CryptBcrypt REQUIRED)

add_executable(test_crypt_bcrypt test_crypt_bcrypt.c)
target_link_libraries(test_crypt_bcrypt CryptBcrypt::CryptBcrypt)

enable_testing()
add_test(NAME test_crypt_bcrypt COMMAND test_crypt_bcrypt)
