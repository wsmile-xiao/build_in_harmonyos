cmake_minimum_required(VERSION 3.15)
project(test_discord-rpc CXX)

# Find the package via Conan-generated CMakeDeps
find_package(discord-rpc REQUIRED)

add_executable(test_discord-rpc test.cpp)
target_link_libraries(test_discord-rpc discord-rpc::discord-rpc)

enable_testing()
add_test(NAME test_discord-rpc COMMAND test_discord-rpc)